from services.publisher_service import publish_to_zhihu
import os

def test_service():
    content = "测试自动发布 - 使用重构后的服务逻辑"
    # 找一个现有的图片测试，如果没有就传 None
    image_paths = ["g.jpg"] if os.path.exists("g.jpg") else []
    
    def progress_callback(msg):
        print(f"[Progress] {msg}")

    try:
        print("开始测试 publisher_service.publish_to_zhihu...")
        success = publish_to_zhihu(content, image_paths=image_paths, progress=progress_callback)
        if success:
            print("--- 服务组件发布测试成功 ---")
        else:
            print("--- 服务组件发布测试失败 (返回 False) ---")
    except Exception as e:
        print(f"--- 服务组件发布测试异常: {e} ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_service()
