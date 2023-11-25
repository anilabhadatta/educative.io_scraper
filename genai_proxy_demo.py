import openai
import base64
import getpass
import os


def main():
    app_name = "data-api-manager-service"

    certificate_path = "/path/to/GAP-proxy-certificate.crt"
    os.environ['REQUESTS_CA_BUNDLE'] = "/Users/amisra/Downloads/GAP-proxy-certificate.crt"

    # password = getpass.getpass(prompt=f"GenAI Password for {app_name}: ")
    password = "KnT5rjEAspq0eIFW"

    genai_proxy_api_key = base64.b64encode(
        f"{app_name}:{password}".encode('ascii')).decode('ascii')

    openai.api_key = genai_proxy_api_key

    openai.api_base = "https://generative-ai-proxy.rcp.us-east-1.data.test.exp-aws.net/v1/proxy/openai/v1"

    max_tokens = 1000  # 50
    print(f"Using max_tokens={max_tokens}")
    messages = []
    message = None
    while True:
        message = input('OpenAI Chat (leave blank to exit): ')
        if message.strip() == '':
            break

        if len(message) / 4 > max_tokens or len(message.split()) > max_tokens:
            print("Message is too long, try something shorter")
            continue

        messages.append({"role": "user", "content": message})
        response = openai.ChatCompletion.create(
            # model="gpt-3.5-turbo",
            model="gpt-4-32k",
            messages=messages,
            max_tokens=max_tokens
        )
        print(response)
        messages.append(response.choices[0].message)
        print(response.choices[0].message.content)

        if len(messages) > 10:
            print("Ten messages is enough, goodbye!")
            break


if __name__ == "__main__":
    main()
