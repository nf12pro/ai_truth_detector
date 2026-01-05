import curses
import json
import requests
import textwrap

API_KEY = "sk-hc-v1-5296baa0916e4ec38c93f257dae9c11ce1ffbe60de064dae9ef0184a479afb34"
API_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"
MODEL = "google/gemini-3-flash-preview"
MAX_QUESTIONS = 5

# stupid hackclubisms
HACK_CLUB_DICT = {
    "HCB": "HCB (Hack Club Bank ; non-profit finance system that takes 7% of total rev)",
    "Hack Club": "Hack Club (a local non-profit for hackathons and coding clubs)",
    "William Daniel": "William Daniel (suspected murderer)",
    "YSWS": "YSWS (You Ship, We Ship ; a hackathon format)"
}

dict_str = "\n".join([f"- {k}: {v}" for k, v in HACK_CLUB_DICT.items()])

SYSTEM_PROMPT = f"""
You are a detective interrogating a suspect regarding a confession they made.
You must ask blunt and relevant questions, avoid being overly verbose.
Try to poke holes in the narrative and attempt to set traps that would catch blatant lies.

Context Definitions:
{dict_str}

Rules:
- Ask at most {MAX_QUESTIONS} clarification questions total.
- Ask one question at a time.
- If you reach the limit, make a best guess.
Final output format:
FINAL ANSWER: TRUE or FALSE
Explanation: short explanation
"""

def query_llm(messages):
    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[System Error]: {str(e)}"

def center_print(stdscr, text, y_offset=0, attr=0):
    h, w = stdscr.getmaxyx()
    x = max(0, (w // 2) - (len(text) // 2))
    y = max(0, (h // 2) + y_offset)
    stdscr.addstr(y, x, text, attr)
    return y, x

def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    
    h, w = stdscr.getmaxyx()

    stdscr.clear()
    prompt = "confess to a crime: "
    py, px = center_print(stdscr, prompt, attr=curses.A_BOLD)
    
    curses.echo()
    curses.curs_set(1)
    
    try:
        input_x = px + len(prompt)
        confession = stdscr.getstr(py, input_x, w - input_x - 1).decode('utf-8')
    except curses.error:
        return

    if not confession.strip():
        return

    curses.noecho()
    curses.curs_set(0)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"I confess: {confession}"}
    ]
    
    history = [("YOU", 2, confession)]
    questions_count = 0

    while True:
        stdscr.clear()
        
        header = f" INTERROGATION (Q: {questions_count}/{MAX_QUESTIONS}) "
        stdscr.addstr(0, (w - len(header)) // 2, header, curses.A_REVERSE)
        
        current_y = h - 4
        
        for role, color, text in reversed(history):
            wrapper = textwrap.TextWrapper(width=w-4)
            lines = wrapper.wrap(text)
            
            if current_y - len(lines) < 1:
                break
                
            for line in reversed(lines):
                stdscr.addstr(current_y, 2, line)
                current_y -= 1
            
            stdscr.addstr(current_y, 2, f"{role}:", curses.color_pair(color) | curses.A_BOLD)
            current_y -= 2

        stdscr.refresh()

        if len(history) % 2 != 0:
            stdscr.addstr(h-2, 2, "Processing...", curses.color_pair(3) | curses.A_BLINK)
            stdscr.refresh()
            
            if questions_count >= MAX_QUESTIONS:
                messages.append({"role": "system", "content": "Limit reached. Output FINAL ANSWER now."})

            response = query_llm(messages)
            history.append(("AI", 1, response))
            
            if "FINAL ANSWER" not in response:
                questions_count += 1
            
            continue

        last_ai_msg = history[-1][2]
        if "FINAL ANSWER" in last_ai_msg:
            stdscr.addstr(h-2, 2, "[CASE CLOSED] Press any key to exit.", curses.A_BOLD)
            stdscr.getch()
            break

        stdscr.hline(h-3, 0, curses.ACS_HLINE, w)
        stdscr.addstr(h-2, 2, "> ")
        
        curses.echo()
        curses.curs_set(1)
        
        try:
            user_input = stdscr.getstr(h-2, 4, w-6).decode('utf-8')
        except curses.error:
            break
            
        curses.noecho()
        curses.curs_set(0)
        
        if not user_input.strip():
            continue

        messages.append({"role": "assistant", "content": last_ai_msg})
        messages.append({"role": "user", "content": user_input})
        history.append(("YOU", 2, user_input))

if __name__ == "__main__":
    curses.wrapper(main)