import os
from openai import OpenAI
from openai.types.chat import (ChatCompletionUserMessageParam)


def main():
    print("Ask your question")
    user_input = input("> ")

    try:
        # Get API key from environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: Please set OPENAI_API_KEY environment variable")
            return

        client = OpenAI(api_key=api_key)

        message = [
            ChatCompletionUserMessageParam(
                role="user",
                content=user_input
            )
        ]
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message,
            max_tokens=500,
            temperature=0.7
        )

        # Extract and print the answer
        answer = response.choices[0].message.content.strip()
        print(f"\nAnswer:\n{answer}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
