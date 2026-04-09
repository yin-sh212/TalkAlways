from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .probe import probe_bacnet, probe_modbus_hosts, probe_modbus_subnet
from .registry import dump_gateway_config_json, validate_gateway_config_payload
from .runtime import EdgeGatewayRuntime


class QueueLogHandler(logging.Handler):
    def __init__(self, event_queue: queue.Queue) -> None:
        super().__init__()
        self.event_queue = event_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self.event_queue.put(("log", message))


class RuntimeWorker:
    def __init__(self, config, event_queue: queue.Queue) -> None:
        self.config = config
        self.event_queue = event_queue
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.runtime: EdgeGatewayRuntime | None = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.thread = threading.Thread(target=self._run, name="edge-gateway-runtime", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.loop and self.runtime and self.running:
            self.event_queue.put(("log", "Stopping gateway runtime..."))
            self.loop.call_soon_threadsafe(self.runtime.request_stop)

    def join(self, timeout: float | None = None) -> None:
        if self.thread:
            self.thread.join(timeout=timeout)

    def _run(self) -> None:
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.runtime = EdgeGatewayRuntime(self.config)
        self.event_queue.put(("runtime_status", "running"))
        self.event_queue.put(("log", f"Gateway started with {len(self.config.enabled_devices)} enabled devices."))

        try:
            self.loop.run_until_complete(self.runtime.run())
        except Exception:
            self.event_queue.put(("runtime_error", traceback.format_exc()))
        finally:
            self.running = False
            self.event_queue.put(("runtime_status", "stopped"))
            if self.loop and not self.loop.is_closed():
                self.loop.close()


class GatewayDesktopApp:
    def __init__(self, root: tk.Tk, initial_config_path: str | None = None) -> None:
        self.root = root
        self.root.title("Semantic IoT Gateway")
        self.root.geometry("1200x820")

        self.event_queue: queue.Queue = queue.Queue()
        self.runtime_worker: RuntimeWorker | None = None
        self.log_handler = QueueLogHandler(self.event_queue)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

        project_root = Path(__file__).resolve().parents[1]
        default_config = project_root / "configs" / "demo_gateway.json"
        self.current_config_path = Path(initial_config_path) if initial_config_path else default_config
        self.config_data: dict = {}

        self.runtime_status_var = tk.StringVar(value="stopped")
        self.config_path_var = tk.StringVar(value=str(self.current_config_path))

        self.modbus_hosts_var = tk.StringVar()
        self.modbus_cidr_var = tk.StringVar()
        self.modbus_port_var = tk.StringVar(value="502")
        self.modbus_timeout_var = tk.StringVar(value="1.0")
        self.modbus_limit_var = tk.StringVar()

        self.bacnet_local_address_var = tk.StringVar()
        self.bacnet_target_address_var = tk.StringVar()
        self.bacnet_timeout_var = tk.StringVar(value="3.0")
        self.bacnet_vendor_id_var = tk.StringVar(value="999")
        self.bacnet_instance_var = tk.StringVar(value="599001")
        self.bacnet_name_var = tk.StringVar(value="SemanticEdgeGateway")
        self.bacnet_network_var = tk.StringVar(value="0")
        self.bacnet_foreign_var = tk.StringVar()
        self.bacnet_ttl_var = tk.StringVar(value="300")

        self._init_form_state()

        self._build_ui()
        self._load_initial_config()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(150, self._drain_events)

    def _init_form_state(self) -> None:
        self.gateway_id_var = tk.StringVar()
        self.site_id_var = tk.StringVar()
        self.output_batch_size_var = tk.StringVar(value="100")
        self.output_flush_interval_var = tk.StringVar(value="1.0")
        self.output_stdout_enabled_var = tk.BooleanVar(value=True)
        self.output_http_enabled_var = tk.BooleanVar(value=False)
        self.output_http_endpoint_var = tk.StringVar()
        self.output_http_token_var = tk.StringVar()
        self.output_http_timeout_var = tk.StringVar(value="5.0")
        self.output_http_verify_var = tk.BooleanVar(value=True)
        self.output_spool_enabled_var = tk.BooleanVar(value=True)
        self.output_spool_path_var = tk.StringVar(value="data/spool.db")
        self.output_spool_retry_interval_var = tk.StringVar(value="5.0")
        self.output_spool_retry_batch_var = tk.StringVar(value="20")

        self.form_bacnet_enabled_var = tk.BooleanVar(value=True)
        self.form_bacnet_local_address_var = tk.StringVar()
        self.form_bacnet_instance_var = tk.StringVar(value="599001")
        self.form_bacnet_name_var = tk.StringVar(value="SemanticEdgeGateway")
        self.form_bacnet_vendor_var = tk.StringVar(value="999")
        self.form_bacnet_network_var = tk.StringVar(value="0")
        self.form_bacnet_foreign_var = tk.StringVar()
        self.form_bacnet_ttl_var = tk.StringVar(value="300")

        self.device_id_form_var = tk.StringVar()
        self.device_name_form_var = tk.StringVar()
        self.device_building_id_form_var = tk.StringVar()
        self.device_type_form_var = tk.StringVar()
        self.device_protocol_form_var = tk.StringVar()
        self.device_host_form_var = tk.StringVar()
        self.device_port_form_var = tk.StringVar()
        self.device_enabled_form_var = tk.BooleanVar(value=True)
        self.device_poll_interval_form_var = tk.StringVar(value="5000")
        self.device_timeout_form_var = tk.StringVar(value="3.0")
        self.device_retry_base_form_var = tk.StringVar(value="1.0")
        self.device_retry_max_form_var = tk.StringVar(value="30.0")
        self.device_retry_multiplier_form_var = tk.StringVar(value="2.0")
        self.device_unit_id_form_var = tk.StringVar(value="1")
        self.device_address_style_form_var = tk.StringVar(value="offset")
        self.device_bacnet_instance_form_var = tk.StringVar()

        self.point_id_form_var = tk.StringVar()
        self.point_tag_form_var = tk.StringVar()
        self.point_standard_tag_form_var = tk.StringVar()
        self.point_unit_form_var = tk.StringVar()
        self.point_scale_form_var = tk.StringVar(value="1.0")
        self.point_offset_form_var = tk.StringVar(value="0.0")
        self.point_deadband_form_var = tk.StringVar()
        self.point_enabled_form_var = tk.BooleanVar(value=True)
        self.point_register_type_form_var = tk.StringVar(value="holding")
        self.point_address_form_var = tk.StringVar()
        self.point_data_type_form_var = tk.StringVar(value="float32")
        self.point_register_count_form_var = tk.StringVar()
        self.point_byte_order_form_var = tk.StringVar(value="big")
        self.point_word_order_form_var = tk.StringVar(value="big")
        self.point_object_type_form_var = tk.StringVar(value="analog-value")
        self.point_object_instance_form_var = tk.StringVar()
        self.point_property_identifier_form_var = tk.StringVar(value="present-value")
        self.point_array_index_form_var = tk.StringVar()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.config_tab = ttk.Frame(notebook)
        self.probe_tab = ttk.Frame(notebook)
        self.runtime_tab = ttk.Frame(notebook)

        notebook.add(self.config_tab, text="配置")
        notebook.add(self.probe_tab, text="探测")
        notebook.add(self.runtime_tab, text="运行")

        self._build_config_tab()
        self._build_probe_tab()
        self._build_runtime_tab()

    def _build_config_tab(self) -> None:
        top = ttk.Frame(self.config_tab)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="配置文件").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.config_path_var, width=85).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="浏览", command=self._browse_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="加载", command=self._load_from_path_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="保存", command=self._save_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="另存为", command=self._save_config_as).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="格式化", command=self._format_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="校验", command=self._validate_config).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="JSON -> 表单", command=self._sync_form_from_editor).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="表单 -> JSON", command=self._sync_editor_from_form).pack(side=tk.LEFT, padx=4)

        config_notebook = ttk.Notebook(self.config_tab)
        config_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        json_tab = ttk.Frame(config_notebook)
        form_tab = ttk.Frame(config_notebook)
        config_notebook.add(form_tab, text="可视化配置")
        config_notebook.add(json_tab, text="JSON")

        self.config_editor = ScrolledText(json_tab, wrap=tk.NONE, font=("Consolas", 10))
        self.config_editor.pack(fill=tk.BOTH, expand=True)

        self._build_form_config_tab(form_tab)

    def _build_form_config_tab(self, parent: ttk.Frame) -> None:
        header = ttk.LabelFrame(parent, text="网关基础配置")
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="Gateway ID").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.gateway_id_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(header, text="Site ID").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.site_id_var, width=24).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)

        ttk.Label(header, text="Batch Size").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_batch_size_var, width=12).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(header, text="Flush Interval").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_flush_interval_var, width=12).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(header, text="Stdout", variable=self.output_stdout_enabled_var).grid(row=1, column=4, sticky=tk.W, padx=8, pady=6)

        ttk.Checkbutton(header, text="HTTP Push", variable=self.output_http_enabled_var).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_http_endpoint_var, width=46).grid(row=2, column=1, columnspan=3, sticky=tk.EW, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_http_token_var, width=24).grid(row=2, column=4, sticky=tk.EW, padx=8, pady=6)

        ttk.Label(header, text="HTTP Timeout").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_http_timeout_var, width=12).grid(row=3, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(header, text="Verify TLS", variable=self.output_http_verify_var).grid(row=3, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(header, text="Spool", variable=self.output_spool_enabled_var).grid(row=3, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_spool_path_var, width=24).grid(row=3, column=4, sticky=tk.EW, padx=8, pady=6)

        ttk.Label(header, text="Spool Retry(s)").grid(row=4, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_spool_retry_interval_var, width=12).grid(row=4, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(header, text="Spool Batch").grid(row=4, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(header, textvariable=self.output_spool_retry_batch_var, width=12).grid(row=4, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Button(header, text="保存基础配置", command=self._save_general_form).grid(row=4, column=4, sticky=tk.E, padx=8, pady=6)

        bacnet_settings = ttk.LabelFrame(parent, text="本地 BACnet 运行参数")
        bacnet_settings.pack(fill=tk.X, pady=(0, 8))
        ttk.Checkbutton(bacnet_settings, text="启用", variable=self.form_bacnet_enabled_var).grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Local Address").grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_local_address_var, width=24).grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Instance").grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_instance_var, width=12).grid(row=0, column=4, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Name").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_name_var, width=24).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Vendor").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_vendor_var, width=12).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Network").grid(row=1, column=4, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_network_var, width=12).grid(row=1, column=5, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="Foreign").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_foreign_var, width=24).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(bacnet_settings, text="TTL").grid(row=2, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_settings, textvariable=self.form_bacnet_ttl_var, width=12).grid(row=2, column=3, sticky=tk.W, padx=8, pady=6)

        device_pane = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        device_pane.pack(fill=tk.BOTH, expand=True)

        device_list_frame = ttk.Frame(device_pane)
        device_detail_frame = ttk.Frame(device_pane)
        device_pane.add(device_list_frame, weight=1)
        device_pane.add(device_detail_frame, weight=3)

        device_list_box_frame = ttk.LabelFrame(device_list_frame, text="设备列表")
        device_list_box_frame.pack(fill=tk.BOTH, expand=True)
        self.device_listbox = tk.Listbox(device_list_box_frame, exportselection=False)
        self.device_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.device_listbox.bind("<<ListboxSelect>>", self._on_device_select)

        device_buttons = ttk.Frame(device_list_frame)
        device_buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(device_buttons, text="新增 Modbus", command=lambda: self._add_device("modbus_tcp")).pack(side=tk.LEFT, padx=4)
        ttk.Button(device_buttons, text="新增 BACnet", command=lambda: self._add_device("bacnet_ip")).pack(side=tk.LEFT, padx=4)
        ttk.Button(device_buttons, text="删除设备", command=self._delete_device).pack(side=tk.LEFT, padx=4)
        ttk.Button(device_buttons, text="保存设备", command=self._save_device_form).pack(side=tk.LEFT, padx=4)

        self._build_device_detail(device_detail_frame)

    def _build_device_detail(self, parent: ttk.Frame) -> None:
        device_frame = ttk.LabelFrame(parent, text="设备详情")
        device_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(device_frame, text="Device ID").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_id_form_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Name").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_name_form_var, width=24).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Building ID").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_building_id_form_var, width=24).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Device Type").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_type_form_var, width=24).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Protocol").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_protocol_form_var, width=20, state="readonly").grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(device_frame, text="Enabled", variable=self.device_enabled_form_var).grid(row=2, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Host").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_host_form_var, width=24).grid(row=3, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Port").grid(row=3, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_port_form_var, width=12).grid(row=3, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Poll(ms)").grid(row=4, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_poll_interval_form_var, width=12).grid(row=4, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Timeout(s)").grid(row=4, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_timeout_form_var, width=12).grid(row=4, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Retry Base").grid(row=5, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_retry_base_form_var, width=12).grid(row=5, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Retry Max").grid(row=5, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_retry_max_form_var, width=12).grid(row=5, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(device_frame, text="Retry Multiplier").grid(row=6, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(device_frame, textvariable=self.device_retry_multiplier_form_var, width=12).grid(row=6, column=1, sticky=tk.W, padx=8, pady=6)

        self.modbus_device_frame = ttk.LabelFrame(device_frame, text="Modbus 参数")
        self.modbus_device_frame.grid(row=7, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=8)
        ttk.Label(self.modbus_device_frame, text="Unit ID").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.modbus_device_frame, textvariable=self.device_unit_id_form_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_device_frame, text="Address Style").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Combobox(
            self.modbus_device_frame,
            textvariable=self.device_address_style_form_var,
            values=("offset", "reference"),
            width=12,
            state="readonly",
        ).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)

        self.bacnet_device_frame = ttk.LabelFrame(device_frame, text="BACnet 参数")
        self.bacnet_device_frame.grid(row=8, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=8)
        ttk.Label(self.bacnet_device_frame, text="Device Instance").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.bacnet_device_frame, textvariable=self.device_bacnet_instance_form_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)

        point_pane = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        point_pane.pack(fill=tk.BOTH, expand=True)

        point_list_frame = ttk.Frame(point_pane)
        point_detail_frame = ttk.Frame(point_pane)
        point_pane.add(point_list_frame, weight=1)
        point_pane.add(point_detail_frame, weight=2)

        point_list_box_frame = ttk.LabelFrame(point_list_frame, text="点位列表")
        point_list_box_frame.pack(fill=tk.BOTH, expand=True)
        self.point_listbox = tk.Listbox(point_list_box_frame, exportselection=False)
        self.point_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.point_listbox.bind("<<ListboxSelect>>", self._on_point_select)

        point_buttons = ttk.Frame(point_list_frame)
        point_buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(point_buttons, text="新增点位", command=self._add_point).pack(side=tk.LEFT, padx=4)
        ttk.Button(point_buttons, text="删除点位", command=self._delete_point).pack(side=tk.LEFT, padx=4)
        ttk.Button(point_buttons, text="保存点位", command=self._save_point_form).pack(side=tk.LEFT, padx=4)

        self._build_point_detail(point_detail_frame)

    def _build_point_detail(self, parent: ttk.Frame) -> None:
        point_frame = ttk.LabelFrame(parent, text="点位详情")
        point_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(point_frame, text="Point ID").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_id_form_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Tag").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_tag_form_var, width=24).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Standard Tag").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_standard_tag_form_var, width=24).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Unit").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_unit_form_var, width=24).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Scale").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_scale_form_var, width=12).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Offset").grid(row=2, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_offset_form_var, width=12).grid(row=2, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(point_frame, text="Deadband").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(point_frame, textvariable=self.point_deadband_form_var, width=12).grid(row=3, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(point_frame, text="Enabled", variable=self.point_enabled_form_var).grid(row=3, column=2, sticky=tk.W, padx=8, pady=6)

        self.modbus_point_frame = ttk.LabelFrame(point_frame, text="Modbus 点位参数")
        self.modbus_point_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=8)
        ttk.Label(self.modbus_point_frame, text="Register Type").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Combobox(
            self.modbus_point_frame,
            textvariable=self.point_register_type_form_var,
            values=("holding", "input", "coil", "discrete"),
            width=12,
            state="readonly",
        ).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_point_frame, text="Address").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.modbus_point_frame, textvariable=self.point_address_form_var, width=12).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_point_frame, text="Data Type").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Combobox(
            self.modbus_point_frame,
            textvariable=self.point_data_type_form_var,
            values=("bool", "uint16", "int16", "uint32", "int32", "float32", "float64", "string"),
            width=12,
            state="readonly",
        ).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_point_frame, text="Reg Count").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.modbus_point_frame, textvariable=self.point_register_count_form_var, width=12).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_point_frame, text="Byte Order").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Combobox(
            self.modbus_point_frame,
            textvariable=self.point_byte_order_form_var,
            values=("big", "little"),
            width=12,
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.modbus_point_frame, text="Word Order").grid(row=2, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Combobox(
            self.modbus_point_frame,
            textvariable=self.point_word_order_form_var,
            values=("big", "little"),
            width=12,
            state="readonly",
        ).grid(row=2, column=3, sticky=tk.W, padx=8, pady=6)

        self.bacnet_point_frame = ttk.LabelFrame(point_frame, text="BACnet 点位参数")
        self.bacnet_point_frame.grid(row=5, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=8)
        ttk.Label(self.bacnet_point_frame, text="Object Type").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.bacnet_point_frame, textvariable=self.point_object_type_form_var, width=18).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.bacnet_point_frame, text="Object Instance").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.bacnet_point_frame, textvariable=self.point_object_instance_form_var, width=12).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.bacnet_point_frame, text="Property").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.bacnet_point_frame, textvariable=self.point_property_identifier_form_var, width=18).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(self.bacnet_point_frame, text="Array Index").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(self.bacnet_point_frame, textvariable=self.point_array_index_form_var, width=12).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)

    def _build_probe_tab(self) -> None:
        modbus_frame = ttk.LabelFrame(self.probe_tab, text="Modbus TCP 单次探测")
        modbus_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(modbus_frame, text="Hosts").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(modbus_frame, textvariable=self.modbus_hosts_var, width=60).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=6)
        ttk.Label(modbus_frame, text="CIDR").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(modbus_frame, textvariable=self.modbus_cidr_var, width=60).grid(row=1, column=1, sticky=tk.EW, padx=8, pady=6)
        ttk.Label(modbus_frame, text="Port").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(modbus_frame, textvariable=self.modbus_port_var, width=10).grid(row=0, column=3, padx=8, pady=6)
        ttk.Label(modbus_frame, text="Timeout").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(modbus_frame, textvariable=self.modbus_timeout_var, width=10).grid(row=1, column=3, padx=8, pady=6)
        ttk.Label(modbus_frame, text="Limit").grid(row=0, column=4, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(modbus_frame, textvariable=self.modbus_limit_var, width=10).grid(row=0, column=5, padx=8, pady=6)
        ttk.Button(modbus_frame, text="开始探测", command=self._run_modbus_probe).grid(row=1, column=5, padx=8, pady=6)
        modbus_frame.columnconfigure(1, weight=1)

        bacnet_frame = ttk.LabelFrame(self.probe_tab, text="BACnet/IP 单次探测")
        bacnet_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        for label, variable in (
            ("Local Address", self.bacnet_local_address_var),
            ("Target Address", self.bacnet_target_address_var),
            ("Device Name", self.bacnet_name_var),
            ("Foreign", self.bacnet_foreign_var),
        ):
            ttk.Label(bacnet_frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=8, pady=6)
            ttk.Entry(bacnet_frame, textvariable=variable, width=45).grid(row=row, column=1, sticky=tk.EW, padx=8, pady=6)
            row += 1

        ttk.Label(bacnet_frame, text="Timeout").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_frame, textvariable=self.bacnet_timeout_var, width=10).grid(row=0, column=3, padx=8, pady=6)
        ttk.Label(bacnet_frame, text="Vendor ID").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_frame, textvariable=self.bacnet_vendor_id_var, width=10).grid(row=1, column=3, padx=8, pady=6)
        ttk.Label(bacnet_frame, text="Instance").grid(row=2, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_frame, textvariable=self.bacnet_instance_var, width=10).grid(row=2, column=3, padx=8, pady=6)
        ttk.Label(bacnet_frame, text="Network").grid(row=3, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_frame, textvariable=self.bacnet_network_var, width=10).grid(row=3, column=3, padx=8, pady=6)
        ttk.Label(bacnet_frame, text="TTL").grid(row=4, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(bacnet_frame, textvariable=self.bacnet_ttl_var, width=10).grid(row=4, column=3, padx=8, pady=6)
        ttk.Button(bacnet_frame, text="开始探测", command=self._run_bacnet_probe).grid(row=4, column=4, padx=8, pady=6)
        bacnet_frame.columnconfigure(1, weight=1)

        result_frame = ttk.LabelFrame(self.probe_tab, text="探测结果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        self.probe_output = ScrolledText(result_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.probe_output.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_runtime_tab(self) -> None:
        controls = ttk.Frame(self.runtime_tab)
        controls.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(controls, text="运行状态").pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=self.runtime_status_var, foreground="#0b5").pack(side=tk.LEFT, padx=8)
        ttk.Button(controls, text="启动网关", command=self._start_runtime).pack(side=tk.LEFT, padx=8)
        ttk.Button(controls, text="停止网关", command=self._stop_runtime).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="清空日志", command=lambda: self._replace_text(self.runtime_output, "")).pack(side=tk.LEFT, padx=4)

        self.runtime_output = ScrolledText(self.runtime_tab, wrap=tk.WORD, font=("Consolas", 10))
        self.runtime_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _sync_form_from_editor(self) -> None:
        config = self._parse_editor_config()
        if not config:
            return
        self.config_data = config.model_dump(mode="json")
        self._load_form_from_config_data()
        self._append_log("Visual form refreshed from JSON editor.")

    def _sync_editor_from_form(self) -> None:
        if not self._capture_form_to_config_data():
            return
        config = validate_gateway_config_payload(self.config_data)
        self._replace_text(self.config_editor, dump_gateway_config_json(config))
        self._append_log("JSON editor refreshed from visual form.")

    def _load_form_from_config_data(self) -> None:
        output = self.config_data.get("output", {})
        http = output.get("http") or {}
        spool = output.get("spool", {})
        bacnet = self.config_data.get("bacnet", {})

        self.gateway_id_var.set(self.config_data.get("gateway_id", ""))
        self.site_id_var.set(self.config_data.get("site_id", ""))
        self.output_batch_size_var.set(str(output.get("batch_size", 100)))
        self.output_flush_interval_var.set(str(output.get("flush_interval_s", 1.0)))
        self.output_stdout_enabled_var.set(bool(output.get("stdout_enabled", True)))
        self.output_http_enabled_var.set(bool(http.get("enabled", False)))
        self.output_http_endpoint_var.set(http.get("endpoint", ""))
        self.output_http_token_var.set(http.get("auth_token", "") or "")
        self.output_http_timeout_var.set(str(http.get("timeout_s", 5.0)))
        self.output_http_verify_var.set(bool(http.get("verify_tls", True)))
        self.output_spool_enabled_var.set(bool(spool.get("enabled", True)))
        self.output_spool_path_var.set(spool.get("path", "data/spool.db"))
        self.output_spool_retry_interval_var.set(str(spool.get("retry_interval_s", 5.0)))
        self.output_spool_retry_batch_var.set(str(spool.get("retry_batch_size", 20)))

        self.form_bacnet_enabled_var.set(bool(bacnet.get("enabled", True)))
        self.form_bacnet_local_address_var.set(bacnet.get("local_address", "") or "")
        self.form_bacnet_instance_var.set(str(bacnet.get("local_device_instance", 599001)))
        self.form_bacnet_name_var.set(bacnet.get("local_device_name", "SemanticEdgeGateway"))
        self.form_bacnet_vendor_var.set(str(bacnet.get("vendor_identifier", 999)))
        self.form_bacnet_network_var.set(str(bacnet.get("network", 0)))
        self.form_bacnet_foreign_var.set(bacnet.get("foreign", "") or "")
        self.form_bacnet_ttl_var.set(str(bacnet.get("ttl", 300)))

        self._refresh_device_list()
        devices = self.config_data.get("devices", [])
        if devices:
            self.device_listbox.selection_clear(0, tk.END)
            self.device_listbox.selection_set(0)
            self._on_device_select()
        else:
            self._clear_device_form()
            self._clear_point_form()

    def _capture_form_to_config_data(self) -> bool:
        try:
            self._save_general_form(show_message=False)
            selected_device = self._current_device_index()
            if selected_device is not None:
                self._save_device_form(show_message=False)
                selected_point = self._current_point_index()
                if selected_point is not None:
                    self._save_point_form(show_message=False)
        except ValueError as exc:
            messagebox.showerror("表单数据错误", str(exc))
            return False
        return True

    def _save_general_form(self, show_message: bool = True) -> None:
        self.config_data["gateway_id"] = self.gateway_id_var.get().strip()
        self.config_data["site_id"] = self.site_id_var.get().strip()
        self.config_data["output"] = {
            "batch_size": int(self.output_batch_size_var.get().strip() or "100"),
            "flush_interval_s": float(self.output_flush_interval_var.get().strip() or "1.0"),
            "stdout_enabled": bool(self.output_stdout_enabled_var.get()),
            "http": {
                "enabled": bool(self.output_http_enabled_var.get()),
                "endpoint": self.output_http_endpoint_var.get().strip(),
                "auth_token": self.output_http_token_var.get().strip() or None,
                "timeout_s": float(self.output_http_timeout_var.get().strip() or "5.0"),
                "verify_tls": bool(self.output_http_verify_var.get()),
            },
            "spool": {
                "enabled": bool(self.output_spool_enabled_var.get()),
                "path": self.output_spool_path_var.get().strip() or "data/spool.db",
                "retry_interval_s": float(self.output_spool_retry_interval_var.get().strip() or "5.0"),
                "retry_batch_size": int(self.output_spool_retry_batch_var.get().strip() or "20"),
            },
        }
        self.config_data["bacnet"] = {
            "enabled": bool(self.form_bacnet_enabled_var.get()),
            "local_address": self.form_bacnet_local_address_var.get().strip() or None,
            "local_device_instance": int(self.form_bacnet_instance_var.get().strip() or "599001"),
            "local_device_name": self.form_bacnet_name_var.get().strip() or "SemanticEdgeGateway",
            "vendor_identifier": int(self.form_bacnet_vendor_var.get().strip() or "999"),
            "network": int(self.form_bacnet_network_var.get().strip() or "0"),
            "foreign": self.form_bacnet_foreign_var.get().strip() or None,
            "ttl": int(self.form_bacnet_ttl_var.get().strip() or "300"),
        }
        if show_message:
            self._append_log("Saved gateway basic settings from visual form.")

    def _refresh_device_list(self) -> None:
        self.device_listbox.delete(0, tk.END)
        for device in self.config_data.get("devices", []):
            label = f"[{device.get('protocol', '-')}] {device.get('device_id', '')} | {device.get('name', '')}"
            self.device_listbox.insert(tk.END, label)

    def _refresh_point_list(self, device_index: int | None = None) -> None:
        self.point_listbox.delete(0, tk.END)
        if device_index is None:
            return
        devices = self.config_data.get("devices", [])
        if not (0 <= device_index < len(devices)):
            return
        for point in devices[device_index].get("points", []):
            label = f"{point.get('point_id', '')} | {point.get('standard_tag', '')}"
            self.point_listbox.insert(tk.END, label)

    def _current_device_index(self) -> int | None:
        selection = self.device_listbox.curselection()
        return selection[0] if selection else None

    def _current_point_index(self) -> int | None:
        selection = self.point_listbox.curselection()
        return selection[0] if selection else None

    def _on_device_select(self, _event=None) -> None:
        index = self._current_device_index()
        if index is None:
            self._clear_device_form()
            self._refresh_point_list(None)
            self._clear_point_form()
            return

        device = self.config_data.get("devices", [])[index]
        retry = device.get("retry_policy", {})
        self.device_id_form_var.set(device.get("device_id", ""))
        self.device_name_form_var.set(device.get("name", ""))
        self.device_building_id_form_var.set(device.get("building_id", ""))
        self.device_type_form_var.set(device.get("device_type", ""))
        self.device_protocol_form_var.set(device.get("protocol", ""))
        self.device_host_form_var.set(device.get("host", ""))
        self.device_port_form_var.set(str(device.get("port", "")))
        self.device_enabled_form_var.set(bool(device.get("enabled", True)))
        self.device_poll_interval_form_var.set(str(device.get("poll_interval_ms", 5000)))
        self.device_timeout_form_var.set(str(device.get("timeout_s", 3.0)))
        self.device_retry_base_form_var.set(str(retry.get("base_delay_s", 1.0)))
        self.device_retry_max_form_var.set(str(retry.get("max_delay_s", 30.0)))
        self.device_retry_multiplier_form_var.set(str(retry.get("multiplier", 2.0)))
        self.device_unit_id_form_var.set(str(device.get("unit_id", 1)))
        self.device_address_style_form_var.set(device.get("address_style", "offset"))
        self.device_bacnet_instance_form_var.set("" if device.get("device_instance") is None else str(device.get("device_instance")))

        self._toggle_protocol_frames(device.get("protocol", ""))
        self._refresh_point_list(index)
        points = device.get("points", [])
        if points:
            self.point_listbox.selection_clear(0, tk.END)
            self.point_listbox.selection_set(0)
            self._on_point_select()
        else:
            self._clear_point_form()

    def _on_point_select(self, _event=None) -> None:
        device_index = self._current_device_index()
        point_index = self._current_point_index()
        if device_index is None or point_index is None:
            self._clear_point_form()
            return

        device = self.config_data.get("devices", [])[device_index]
        points = device.get("points", [])
        if not (0 <= point_index < len(points)):
            self._clear_point_form()
            return

        point = points[point_index]
        self.point_id_form_var.set(point.get("point_id", ""))
        self.point_tag_form_var.set(point.get("tag", ""))
        self.point_standard_tag_form_var.set(point.get("standard_tag", ""))
        self.point_unit_form_var.set(point.get("unit", "") or "")
        self.point_scale_form_var.set(str(point.get("scale", 1.0)))
        self.point_offset_form_var.set(str(point.get("offset", 0.0)))
        self.point_deadband_form_var.set("" if point.get("deadband") is None else str(point.get("deadband")))
        self.point_enabled_form_var.set(bool(point.get("enabled", True)))

        protocol = device.get("protocol", "")
        if protocol == "modbus_tcp":
            self.point_register_type_form_var.set(point.get("register_type", "holding"))
            self.point_address_form_var.set(str(point.get("address", "")))
            self.point_data_type_form_var.set(point.get("data_type", "float32"))
            self.point_register_count_form_var.set("" if point.get("register_count") is None else str(point.get("register_count")))
            self.point_byte_order_form_var.set(point.get("byte_order", "big"))
            self.point_word_order_form_var.set(point.get("word_order", "big"))
        else:
            self.point_object_type_form_var.set(point.get("object_type", "analog-value"))
            self.point_object_instance_form_var.set(str(point.get("object_instance", "")))
            self.point_property_identifier_form_var.set(point.get("property_identifier", "present-value"))
            self.point_array_index_form_var.set("" if point.get("array_index") is None else str(point.get("array_index")))

        self._toggle_protocol_frames(protocol)

    def _toggle_protocol_frames(self, protocol: str) -> None:
        if protocol == "modbus_tcp":
            self.modbus_device_frame.grid()
            self.modbus_point_frame.grid()
            self.bacnet_device_frame.grid_remove()
            self.bacnet_point_frame.grid_remove()
        elif protocol == "bacnet_ip":
            self.bacnet_device_frame.grid()
            self.bacnet_point_frame.grid()
            self.modbus_device_frame.grid_remove()
            self.modbus_point_frame.grid_remove()
        else:
            self.modbus_device_frame.grid_remove()
            self.modbus_point_frame.grid_remove()
            self.bacnet_device_frame.grid_remove()
            self.bacnet_point_frame.grid_remove()

    def _clear_device_form(self) -> None:
        for variable in (
            self.device_id_form_var,
            self.device_name_form_var,
            self.device_building_id_form_var,
            self.device_type_form_var,
            self.device_protocol_form_var,
            self.device_host_form_var,
            self.device_port_form_var,
            self.device_poll_interval_form_var,
            self.device_timeout_form_var,
            self.device_retry_base_form_var,
            self.device_retry_max_form_var,
            self.device_retry_multiplier_form_var,
            self.device_unit_id_form_var,
            self.device_address_style_form_var,
            self.device_bacnet_instance_form_var,
        ):
            variable.set("")
        self.device_enabled_form_var.set(False)
        self._toggle_protocol_frames("")

    def _clear_point_form(self) -> None:
        for variable in (
            self.point_id_form_var,
            self.point_tag_form_var,
            self.point_standard_tag_form_var,
            self.point_unit_form_var,
            self.point_scale_form_var,
            self.point_offset_form_var,
            self.point_deadband_form_var,
            self.point_register_type_form_var,
            self.point_address_form_var,
            self.point_data_type_form_var,
            self.point_register_count_form_var,
            self.point_byte_order_form_var,
            self.point_word_order_form_var,
            self.point_object_type_form_var,
            self.point_object_instance_form_var,
            self.point_property_identifier_form_var,
            self.point_array_index_form_var,
        ):
            variable.set("")
        self.point_enabled_form_var.set(False)

    def _add_device(self, protocol: str) -> None:
        self._save_general_form(show_message=False)
        devices = self.config_data.setdefault("devices", [])
        next_index = len(devices) + 1
        if protocol == "modbus_tcp":
            new_device = {
                "device_id": f"modbus-device-{next_index:02d}",
                "name": f"Modbus Device {next_index}",
                "building_id": "",
                "device_type": "modbus_device",
                "protocol": "modbus_tcp",
                "host": "",
                "port": 502,
                "enabled": True,
                "poll_interval_ms": 5000,
                "timeout_s": 3.0,
                "unit_id": 1,
                "address_style": "offset",
                "retry_policy": {"base_delay_s": 1.0, "max_delay_s": 30.0, "multiplier": 2.0},
                "points": [],
            }
        else:
            new_device = {
                "device_id": f"bacnet-device-{next_index:02d}",
                "name": f"BACnet Device {next_index}",
                "building_id": "",
                "device_type": "bacnet_device",
                "protocol": "bacnet_ip",
                "host": "",
                "port": 47808,
                "enabled": True,
                "poll_interval_ms": 5000,
                "timeout_s": 3.0,
                "device_instance": None,
                "retry_policy": {"base_delay_s": 1.0, "max_delay_s": 30.0, "multiplier": 2.0},
                "points": [],
            }
        devices.append(new_device)
        self._refresh_device_list()
        last_index = len(devices) - 1
        self.device_listbox.selection_clear(0, tk.END)
        self.device_listbox.selection_set(last_index)
        self._on_device_select()
        self._append_log(f"Added {protocol} device template.")

    def _delete_device(self) -> None:
        index = self._current_device_index()
        if index is None:
            return
        devices = self.config_data.get("devices", [])
        if not (0 <= index < len(devices)):
            return
        removed = devices.pop(index)
        self._refresh_device_list()
        self._refresh_point_list(None)
        self._clear_device_form()
        self._clear_point_form()
        self._append_log(f"Deleted device: {removed.get('device_id', '')}")

    def _save_device_form(self, show_message: bool = True) -> None:
        index = self._current_device_index()
        if index is None:
            return
        devices = self.config_data.get("devices", [])
        if not (0 <= index < len(devices)):
            return
        device = devices[index]
        protocol = device.get("protocol", "")
        existing_points = device.get("points", [])

        updated = {
            "device_id": self.device_id_form_var.get().strip(),
            "name": self.device_name_form_var.get().strip(),
            "building_id": self.device_building_id_form_var.get().strip(),
            "device_type": self.device_type_form_var.get().strip(),
            "protocol": protocol,
            "host": self.device_host_form_var.get().strip(),
            "port": int(self.device_port_form_var.get().strip() or ("502" if protocol == "modbus_tcp" else "47808")),
            "enabled": bool(self.device_enabled_form_var.get()),
            "poll_interval_ms": int(self.device_poll_interval_form_var.get().strip() or "5000"),
            "timeout_s": float(self.device_timeout_form_var.get().strip() or "3.0"),
            "retry_policy": {
                "base_delay_s": float(self.device_retry_base_form_var.get().strip() or "1.0"),
                "max_delay_s": float(self.device_retry_max_form_var.get().strip() or "30.0"),
                "multiplier": float(self.device_retry_multiplier_form_var.get().strip() or "2.0"),
            },
            "points": existing_points,
        }
        if protocol == "modbus_tcp":
            updated["unit_id"] = int(self.device_unit_id_form_var.get().strip() or "1")
            updated["address_style"] = self.device_address_style_form_var.get().strip() or "offset"
        else:
            updated["device_instance"] = (
                int(self.device_bacnet_instance_form_var.get().strip())
                if self.device_bacnet_instance_form_var.get().strip()
                else None
            )

        devices[index] = updated
        self._refresh_device_list()
        self.device_listbox.selection_clear(0, tk.END)
        self.device_listbox.selection_set(index)
        if show_message:
            self._append_log(f"Saved device: {updated['device_id']}")

    def _add_point(self) -> None:
        device_index = self._current_device_index()
        if device_index is None:
            messagebox.showwarning("缺少设备", "请先选择一个设备。")
            return
        self._save_device_form(show_message=False)
        device = self.config_data.get("devices", [])[device_index]
        points = device.setdefault("points", [])
        next_index = len(points) + 1
        if device.get("protocol") == "modbus_tcp":
            point = {
                "point_id": f"modbus_point_{next_index:02d}",
                "tag": f"ModbusPoint{next_index}",
                "standard_tag": "unknown",
                "unit": "",
                "scale": 1.0,
                "offset": 0.0,
                "deadband": None,
                "enabled": True,
                "register_type": "holding",
                "address": 0,
                "data_type": "float32",
                "register_count": 2,
                "byte_order": "big",
                "word_order": "big",
            }
        else:
            point = {
                "point_id": f"bacnet_point_{next_index:02d}",
                "tag": f"BacnetPoint{next_index}",
                "standard_tag": "unknown",
                "unit": "",
                "scale": 1.0,
                "offset": 0.0,
                "deadband": None,
                "enabled": True,
                "object_type": "analog-value",
                "object_instance": next_index,
                "property_identifier": "present-value",
                "array_index": None,
            }
        points.append(point)
        self._refresh_point_list(device_index)
        last_index = len(points) - 1
        self.point_listbox.selection_clear(0, tk.END)
        self.point_listbox.selection_set(last_index)
        self._on_point_select()
        self._append_log(f"Added point template to {device.get('device_id', '')}.")

    def _delete_point(self) -> None:
        device_index = self._current_device_index()
        point_index = self._current_point_index()
        if device_index is None or point_index is None:
            return
        device = self.config_data.get("devices", [])[device_index]
        points = device.get("points", [])
        if not (0 <= point_index < len(points)):
            return
        removed = points.pop(point_index)
        self._refresh_point_list(device_index)
        self._clear_point_form()
        self._append_log(f"Deleted point: {removed.get('point_id', '')}")

    def _save_point_form(self, show_message: bool = True) -> None:
        device_index = self._current_device_index()
        point_index = self._current_point_index()
        if device_index is None or point_index is None:
            return
        device = self.config_data.get("devices", [])[device_index]
        points = device.get("points", [])
        if not (0 <= point_index < len(points)):
            return

        point = {
            "point_id": self.point_id_form_var.get().strip(),
            "tag": self.point_tag_form_var.get().strip(),
            "standard_tag": self.point_standard_tag_form_var.get().strip(),
            "unit": self.point_unit_form_var.get().strip() or None,
            "scale": float(self.point_scale_form_var.get().strip() or "1.0"),
            "offset": float(self.point_offset_form_var.get().strip() or "0.0"),
            "deadband": float(self.point_deadband_form_var.get().strip()) if self.point_deadband_form_var.get().strip() else None,
            "enabled": bool(self.point_enabled_form_var.get()),
        }
        if device.get("protocol") == "modbus_tcp":
            point.update(
                {
                    "register_type": self.point_register_type_form_var.get().strip() or "holding",
                    "address": int(self.point_address_form_var.get().strip() or "0"),
                    "data_type": self.point_data_type_form_var.get().strip() or "float32",
                    "register_count": int(self.point_register_count_form_var.get().strip()) if self.point_register_count_form_var.get().strip() else None,
                    "byte_order": self.point_byte_order_form_var.get().strip() or "big",
                    "word_order": self.point_word_order_form_var.get().strip() or "big",
                }
            )
        else:
            point.update(
                {
                    "object_type": self.point_object_type_form_var.get().strip() or "analog-value",
                    "object_instance": int(self.point_object_instance_form_var.get().strip() or "0"),
                    "property_identifier": self.point_property_identifier_form_var.get().strip() or "present-value",
                    "array_index": int(self.point_array_index_form_var.get().strip()) if self.point_array_index_form_var.get().strip() else None,
                }
            )
        points[point_index] = point
        self._refresh_point_list(device_index)
        self.point_listbox.selection_clear(0, tk.END)
        self.point_listbox.selection_set(point_index)
        if show_message:
            self._append_log(f"Saved point: {point['point_id']}")

    def _load_initial_config(self) -> None:
        if self.current_config_path.exists():
            self._load_config_from_path(self.current_config_path)
        else:
            self.config_data = {}
            self._replace_text(self.config_editor, "{}")

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="选择网关配置文件",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self.config_path_var.set(path)
            self._load_config_from_path(Path(path))

    def _load_from_path_var(self) -> None:
        self._load_config_from_path(Path(self.config_path_var.get()))

    def _load_config_from_path(self, path: Path) -> None:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("加载失败", str(exc))
            return

        try:
            payload = json.loads(raw_text)
            config = validate_gateway_config_payload(payload)
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return

        self.current_config_path = path
        self.config_path_var.set(str(path))
        self.config_data = config.model_dump(mode="json")
        self._replace_text(self.config_editor, dump_gateway_config_json(config))
        self._load_form_from_config_data()
        self._append_log(f"Loaded config: {path}")

    def _save_config(self) -> None:
        if not self.config_path_var.get().strip():
            self._save_config_as()
            return
        self._save_to_path(Path(self.config_path_var.get()))

    def _save_config_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存网关配置",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self._save_to_path(Path(path))

    def _save_to_path(self, path: Path) -> None:
        if not self._capture_form_to_config_data():
            return
        try:
            config = validate_gateway_config_payload(self.config_data)
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dump_gateway_config_json(config), encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return

        self.current_config_path = path
        self.config_path_var.set(str(path))
        self.config_data = config.model_dump(mode="json")
        self._replace_text(self.config_editor, dump_gateway_config_json(config))
        self._load_form_from_config_data()
        self._append_log(f"Saved config: {path}")

    def _format_config(self) -> None:
        config = self._parse_editor_config()
        if config:
            self.config_data = config.model_dump(mode="json")
            self._replace_text(self.config_editor, dump_gateway_config_json(config))
            self._load_form_from_config_data()

    def _validate_config(self) -> None:
        if not self._capture_form_to_config_data():
            return
        try:
            config = validate_gateway_config_payload(self.config_data)
        except Exception as exc:
            messagebox.showerror("配置解析失败", str(exc))
            return
        if not config:
            return
        self.config_data = config.model_dump(mode="json")
        self._replace_text(self.config_editor, dump_gateway_config_json(config))
        messagebox.showinfo(
            "配置有效",
            f"Gateway: {config.gateway_id}\nSite: {config.site_id}\nDevices: {len(config.devices)}\nEnabled: {len(config.enabled_devices)}",
        )

    def _parse_editor_config(self):
        try:
            payload = json.loads(self.config_editor.get("1.0", tk.END).strip() or "{}")
            return validate_gateway_config_payload(payload)
        except Exception as exc:
            messagebox.showerror("配置解析失败", str(exc))
            return None

    def _run_modbus_probe(self) -> None:
        try:
            port = int(self.modbus_port_var.get().strip() or "502")
            timeout = float(self.modbus_timeout_var.get().strip() or "1.0")
            limit = int(self.modbus_limit_var.get().strip()) if self.modbus_limit_var.get().strip() else None
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        hosts_value = self.modbus_hosts_var.get().strip()
        cidr_value = self.modbus_cidr_var.get().strip()
        if not hosts_value and not cidr_value:
            messagebox.showwarning("缺少参数", "请填写 Hosts 或 CIDR。")
            return

        self._append_probe("Starting Modbus probe...")

        def worker() -> None:
            try:
                if hosts_value:
                    hosts = [item.strip() for item in hosts_value.split(",") if item.strip()]
                    result = asyncio.run(probe_modbus_hosts(hosts, port=port, timeout_s=timeout))
                else:
                    result = asyncio.run(probe_modbus_subnet(cidr_value, port=port, timeout_s=timeout, limit=limit))
                self.event_queue.put(("probe_result", [item.model_dump(mode="json") for item in result]))
            except Exception:
                self.event_queue.put(("probe_error", traceback.format_exc()))

        threading.Thread(target=worker, daemon=True).start()

    def _run_bacnet_probe(self) -> None:
        try:
            timeout = float(self.bacnet_timeout_var.get().strip() or "3.0")
            vendor_id = int(self.bacnet_vendor_id_var.get().strip() or "999")
            instance = int(self.bacnet_instance_var.get().strip() or "599001")
            network = int(self.bacnet_network_var.get().strip() or "0")
            ttl = int(self.bacnet_ttl_var.get().strip() or "300")
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self._append_probe("Starting BACnet probe...")

        def worker() -> None:
            try:
                result = asyncio.run(
                    probe_bacnet(
                        local_address=self.bacnet_local_address_var.get().strip() or None,
                        timeout_s=timeout,
                        target_address=self.bacnet_target_address_var.get().strip() or None,
                        vendor_identifier=vendor_id,
                        local_device_instance=instance,
                        local_device_name=self.bacnet_name_var.get().strip() or "SemanticEdgeGateway",
                        network=network,
                        foreign=self.bacnet_foreign_var.get().strip() or None,
                        ttl=ttl,
                    )
                )
                self.event_queue.put(("probe_result", [item.model_dump(mode="json") for item in result]))
            except Exception:
                self.event_queue.put(("probe_error", traceback.format_exc()))

        threading.Thread(target=worker, daemon=True).start()

    def _start_runtime(self) -> None:
        if self.runtime_worker and self.runtime_worker.running:
            messagebox.showinfo("运行中", "网关已经在运行。")
            return

        if not self._capture_form_to_config_data():
            return
        try:
            config = validate_gateway_config_payload(self.config_data)
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return

        self.config_data = config.model_dump(mode="json")
        self._replace_text(self.config_editor, dump_gateway_config_json(config))
        self.runtime_worker = RuntimeWorker(config, self.event_queue)
        self.runtime_status_var.set("starting")
        self.runtime_worker.start()

    def _stop_runtime(self) -> None:
        if not self.runtime_worker or not self.runtime_worker.running:
            self.runtime_status_var.set("stopped")
            return
        self.runtime_status_var.set("stopping")
        self.runtime_worker.stop()

    def _append_probe(self, message: str) -> None:
        self.probe_output.insert(tk.END, f"{message}\n")
        self.probe_output.see(tk.END)

    def _append_log(self, message: str) -> None:
        self.runtime_output.insert(tk.END, f"{message}\n")
        self.runtime_output.see(tk.END)

    def _replace_text(self, widget: ScrolledText, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def _drain_events(self) -> None:
        while True:
            try:
                event_type, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "log":
                self._append_log(payload)
            elif event_type == "probe_result":
                self._append_probe(json.dumps(payload, ensure_ascii=False, indent=2))
            elif event_type == "probe_error":
                self._append_probe(payload)
                messagebox.showerror("探测失败", payload)
            elif event_type == "runtime_status":
                self.runtime_status_var.set(payload)
                self._append_log(f"Runtime status: {payload}")
            elif event_type == "runtime_error":
                self.runtime_status_var.set("error")
                self._append_log(payload)
                messagebox.showerror("运行异常", payload)

        self.root.after(150, self._drain_events)

    def _on_close(self) -> None:
        if self.runtime_worker and self.runtime_worker.running:
            if not messagebox.askyesno("退出", "网关仍在运行，是否先停止再退出？"):
                return
            self._stop_runtime()
            self.runtime_worker.join(timeout=3.0)

        logging.getLogger().removeHandler(self.log_handler)
        self.root.destroy()


def launch_gui(initial_config_path: str | None = None) -> int:
    root = tk.Tk()
    app = GatewayDesktopApp(root, initial_config_path=initial_config_path)
    root.mainloop()
    return 0
