from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# 你的分享链接
url = "https://2f34c8d8.r20.cpolar.top/next-chats/share?shared_id=57e08ebe1c8911f1993735fb68817e6f&from=chat&auth=5V4y8t_ydGvUal3YSbFRSNzDYQj7-Dnn&theme=light"

# 初始化浏览器
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 如果不想显示浏览器界面，取消这行注释
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    print(f"正在访问：{url}")
    driver.get(url)

    # 等待页面加载 (这里简单等待 5 秒，实际可以用 WebDriverWait)
    time.sleep(5)

    # --- 自动化发送消息示例 ---
    # 注意：NextChat 的输入框 class 可能会变，需要根据实际 F12 查看调整
    # 这里尝试通过 placeholder 或常见 class 定位输入框
    try:
        # 尝试查找输入框 (常见的 NextChat 输入框选择器)
        input_box = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='输入']")
        # 或者 By.CLASS_NAME, "input-box" 等

        message = "你好，请介绍一下你自己"
        input_box.send_keys(message)
        input_box.send_keys(Keys.ENTER)  # 模拟回车发送

        print("消息已发送，等待回复...")
        time.sleep(10)  # 等待 AI 回复

        # 这里可以添加代码来提取回复内容
        # print(driver.page_source)

    except Exception as e:
        print(f"未找到输入框或发送失败：{e}")
        print("可能页面还在加载，或者选择器需要调整。")

    # 保持浏览器打开一会让你观察
    time.sleep(10)

finally:
    driver.quit()