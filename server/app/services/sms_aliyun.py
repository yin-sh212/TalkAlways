# app/services/sms_aliyun.py
from aliyunsdkcore.client import AcsClient
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
import json
import os
from dotenv import load_dotenv
import sys
import io

# 修复编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()


class AliyunSMSService:
    """阿里云短信服务"""

    def __init__(self):
        self.access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        self.access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        self.sign_name = os.getenv('ALIYUN_SMS_SIGN_NAME')
        self.template_code = os.getenv('ALIYUN_SMS_TEMPLATE_CODE')

        # 检查配置是否完整
        self.enabled = all([self.access_key_id, self.access_key_secret, self.sign_name, self.template_code])

        if self.enabled:
            try:
                # 初始化客户端（区域用cn-hangzhou）
                self.client = AcsClient(
                    self.access_key_id,
                    self.access_key_secret,
                    'cn-hangzhou'
                )
                print("✅ 阿里云短信服务初始化成功")
            except Exception as e:
                print(f"⚠️ 阿里云短信初始化失败: {e}")
                self.enabled = False
        else:
            print("⚠️ 阿里云短信配置不完整，使用模拟模式")
            print(f"AccessKeyId: {'已配置' if self.access_key_id else '未配置'}")
            print(f"AccessKeySecret: {'已配置' if self.access_key_secret else '未配置'}")
            print(f"签名: {'已配置' if self.sign_name else '未配置'}")
            print(f"模板CODE: {'已配置' if self.template_code else '未配置'}")

    def send_sms(self, phone: str, code: str) -> bool:
        """
        发送短信验证码
        """
        # 模拟模式
        if not self.enabled:
            print(f"\n📨 ===== 模拟发送验证码 ======")
            print(f"📱 手机号: {phone}")
            print(f"🔑 验证码: {code}")
            print(f"========================\n")
            return True

        try:
            # 构建请求
            request = SendSmsRequest.SendSmsRequest()
            request.set_PhoneNumbers(phone)
            request.set_SignName(self.sign_name)
            request.set_TemplateCode(self.template_code)

            # 模板参数（验证码和有效期）
            template_param = json.dumps({"code": code, "minute": "5"})
            request.set_TemplateParam(template_param)

            print(f"📤 正在发送短信到 {phone}...")

            # 发送短信
            response = self.client.do_action_with_exception(request)
            response_json = json.loads(response)

            # 打印日志
            print(f"\n📨 阿里云短信发送结果:")
            print(f"手机号: {phone}")
            print(f"验证码: {code}")
            print(f"状态码: {response_json.get('Code')}")
            print(f"状态描述: {response_json.get('Message')}")
            print(f"请求ID: {response_json.get('RequestId')}")
            print("========================\n")

            # 判断是否成功（Code=OK表示成功）
            return response_json.get('Code') == 'OK'

        except Exception as e:
            print(f"❌ 阿里云短信发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 全局实例
aliyun_sms = AliyunSMSService()