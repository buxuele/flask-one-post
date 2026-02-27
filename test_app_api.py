import requests
import time
import json

def test_publish():
    url = "http://localhost:5000/api/publish"
    data = {
        "content": "测试环境自动发布测试 - Agent",
        "platforms": ["zhihu"],
        "image_paths": []
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=data)
        res_json = response.json()
        print(f"Response: {res_json}")
        
        if res_json.get('success'):
            job_id = res_json['job_id']
            print(f"Job created: {job_id}. Checking status...")
            
            # Poll status
            for _ in range(30):
                status_res = requests.get(f"http://localhost:5000/api/publish/status/{job_id}")
                status_data = status_res.json()
                job = status_data.get('job', {})
                status = job.get('status')
                
                print(f"[{time.strftime('%H:%M:%S')}] Status: {status}")
                if status in ['done', 'error']:
                    print(f"Final Job Data: {json.dumps(job, indent=2, ensure_ascii=False)}")
                    break
                
                time.sleep(3)
        else:
            print("Failed to start publish job.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_publish()
