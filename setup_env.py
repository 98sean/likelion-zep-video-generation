import os

ENV_FILE = ".env"

def create_env_file():
    print("🔧 .env 설정을 시작합니다.\n")

    openai_key = input("👉 OpenAI API Key를 입력하세요: ").strip()
    serpapi_key = input("👉 SerpAPI API Key를 입력하세요 (없으면 Enter): ").strip()

    # .env 내용 구성
    content = f"OPENAI_API_KEY={openai_key}\n"
    if serpapi_key:
        content += f"SERPAPI_API_KEY={serpapi_key}\n"

    # 파일 생성
    with open(ENV_FILE, "w") as f:
        f.write(content)

    print("\n🎉 .env 파일이 성공적으로 생성되었습니다!")
    print("📄 생성된 내용:")
    print("--------------------------------")
    print(content)
    print("--------------------------------")
    print("\n⚠️ 반드시 .gitignore에 `.env`를 추가하세요! (유출 위험 방지)")

if __name__ == "__main__":
    create_env_file()
