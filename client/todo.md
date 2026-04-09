1. 能耗数据表重构
 评估并迁移至时序数据库(TSDB)

调研 InfluxDB/TDengine/Prometheus 方案
设计 energy_consumption 新表结构(时间戳+指标键值对)
实现数据迁移脚本(历史数据导入 TSDB)
修改后端 API 查询逻辑适配 TSDB 聚合函数
 重构字段设计提升扩展性

将硬编码字段(electricity, cooling_load等)改为 metric_name + metric_value 键值对
或采用 JSON 字段存储多类型能耗指标
更新相关 CRUD 接口和前端展示逻辑
2. 告警表增强
 添加审计追踪字段
在 alarms 表增加: acknowledged_by, acknowledged_at, resolved_by, resolved_at
修改确认/解决告警接口,记录操作人 ID 和时间
前端告警详情页面展示操作历史记录
3. 用户权限体系
 实现 RBAC 模型
创建 roles 表和 user_roles 关联表
定义角色: 普通操作员、审核员、系统管理员
在后端中间件中添加权限校验逻辑
前端根据角色动态显示菜单和操作按钮
4. 设备资产模型统一
 合并 devices 和 meters 表
设计统一资产表 assets,增加 asset_type 字段区分电表/空调/其他设备
修改 energy_consumption 外键从 meter_id 改为 asset_id
修改 alarms 表统一使用 asset_id
更新所有关联查询和业务逻辑
AI 业务逻辑优化
5. 知识库质量管控
 增加审核流程
在知识库表增加 status 字段(draft/reviewed/approved)
告警解决方案入库时默认标记为 draft
新增管理员审核接口和前端审核页面
RAG 检索时仅返回 approved 状态的知识条目
6. 管控能力落地
 明确管控边界并实现
确认需求:是"自动下发指令"还是"生成人工建议"
若需自动控制:
创建设备控制指令表 device_commands(指令内容、执行状态、结果反馈)
开发反控网关接口对接底层设备
增加指令下发日志和失败重试机制
若仅辅助决策:
在 AI 分析结果中明确标注"建议操作"
增加运维人员执行反馈闭环
7. AI 图表分析优化
 改造悬浮球数据传递方式
前端提取当前图表的 JSON 数据(关键统计值、趋势点、异常点)
打包查询条件(时间范围、建筑ID、指标类型)
调用 /api/ai-analyst/analyze-chart 时传入结构化数据而非图片
后端 Prompt 模板强调基于数值进行因果推理
确保流式输出性能(首包<3s,总耗时<30s)
优先级建议
P0 (立即处理):

问题 7(AI 图表分析):直接影响当前功能准确性
问题 5(知识库污染):避免垃圾数据累积
P1 (近期迭代):

问题 1(能耗表重构):涉及核心数据存储,需充分测试
问题 2(告警审计):运维管理刚需
P2 (中长期规划):

问题 3(RBAC):取决于团队规模和权限需求复杂度
问题 4(资产统一):需协调前后端大量改动
问题 6(管控能力):需明确业务需求和硬件对接方案