# app/services/sms_tencent.py
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.sms.v20210111 import sms_client, models
import os
from dotenv import load_dotenv
import sys
import io

# 修复编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()


class TencentSMSService:
    """腾讯云短信服务"""

    def __init__(self):
        self.secret_id = os.getenv('TENCENT_SECRET_ID')
        self.secret_key = os.getenv('TENCENT_SECRET_KEY')
        self.sms_sign = os.getenv('TENCENT_SMS_SIGN')
        self.template_id = os.getenv('TENCENT_SMS_TEMPLATE_ID')
        self.app_id = os.getenv('TENCENT_SMS_APP_ID')

        # 如果没有配置，就使用模拟模式
        self.enabled = all([self.secret_id, self.secret_key, self.sms_sign, self.template_id, self.app_id])

        if self.enabled:
            try:
                # 初始化认证
                self.cred = credential.Credential(self.secret_id, self.secret_key)

                # 配置HTTP
                http_profile = HttpProfile()
                http_profile.endpoint = "sms.tencentcloudapi.com"

                # 配置客户端
                client_profile = ClientProfile()
                client_profile.httpProfile = http_profile
                self.client = sms_client.SmsClient(self.cred, "ap-guangzhou", client_profile)
                print("✅ 腾讯云短信服务初始化成功")
            except Exception as e:
                print(f"⚠️ 腾讯云短信初始化失败，使用模拟模式: {e}")
                self.enabled = False
        else:
            print("⚠️ 腾讯云短信未配置，使用模拟模式")

    def send_sms(self, phone: str, code: str) -> bool:
        """
        发送短信验证码
        """
        # 模拟模式
        if not self.enabled:
            print(f"\n📨 ===== 模拟发送验证码 ======")
            print(f"📱 手机号: {phone}")
            print(f"🔑 验证码: {code}")
            print(f"⏱️  有效期: 5分钟")
            print(f"========================\n")
            return True

        try:
            req = models.SendSmsRequest()

            # 设置手机号（腾讯云需要加国家码）
            req.PhoneNumberSet = ["+86" + phone]

            # 设置模板参数
            req.SmsSdkAppId = self.app_id
            req.SignName = self.sms_sign
            req.TemplateId = self.template_id

            # 模板参数（你的模板里要有{1}占位符）
            req.TemplateParamSet = [code]

            # 发送短信
            resp = self.client.SendSms(req)

            # 打印日志
            print(f"\n📨 腾讯云短信发送结果:")
            print(f"手机号: {phone}")
            print(f"验证码: {code}")
            print(f"状态: {resp.SendStatusSet[0].Code}")
            print(f"消息: {resp.SendStatusSet[0].Message}")
            print("========================\n")

            # 判断是否成功
            return resp.SendStatusSet[0].Code == "Ok"

        except Exception as e:
            print(f"❌ 腾讯云短信发送失败: {e}")
            print("使用模拟模式继续...")
            print(f"\n📨 ===== 模拟发送验证码 ======")
            print(f"📱 手机号: {phone}")
            print(f"🔑 验证码: {code}")
            print(f"========================\n")
            return True


# 全局实例
tencent_sms = TencentSMSService()