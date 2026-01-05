import requests
import sys

#region Config

API_KEY = "sk-hc-v1-5296baa0916e4ec38c93f257dae9c11ce1ffbe60de064dae9ef0184a479afb34"

# Hack Club proxy endpoint (CORRECT)
API_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"

MODEL = "mistralai/mistral-7b-instruct"
MAX_QUESTIONS = 5

SYSTEM_PROMPT = """
You verify user claims.

Rules:
- Ask at most 5 clarification questions total.
- Ask one question at a time.
- Only ask useful questions.
- If you reach the limit, make a best guess.

Final output format (exactly):
FINAL ANSWER: TRUE or FALSE
Explanation: short explanation

Do not ask questions after the final answer.
"""

#endregion

#region Functions

def ask_ai(messages):
	response = requests.post(
		API_URL,
		headers={
			"Authorization": f"Bearer {API_KEY}",
			"Content-Type": "application/json",
		},
		json={
			"model": MODEL,
			"messages": messages,
		},
		timeout=30
	)

	data = response.json()

	# Handle API errors cleanly
	if "choices" not in data:
		print("\n❌ API ERROR RESPONSE:")
		print(data)
		sys.exit(1)

	return data["choices"][0]["message"]["content"]

# ================= MAIN PROGRAM =================

print("=== Claim Verification AI ===")
claim = input("Enter your claim: ")

messages = [
	{"role": "system", "content": SYSTEM_PROMPT},
	{"role": "user", "content": claim},
]

questions_asked = 0

while True:
	reply = ask_ai(messages)
	print("\nAI:", reply)

	# Stop if AI decided
	if "FINAL ANSWER:" in reply:
		break

	questions_asked += 1

	# Force decision at question limit
	if questions_asked >= MAX_QUESTIONS:
		messages.append({"role": "assistant", "content": reply})
		messages.append({
			"role": "system",
			"content": "You have reached the question limit. Decide now."
		})
		final_reply = ask_ai(messages)
		print("\nAI:", final_reply)
		break

	user_input = input("\nYour answer: ")
	messages.append({"role": "assistant", "content": reply})
	messages.append({"role": "user", "content": user_input})

#endregion