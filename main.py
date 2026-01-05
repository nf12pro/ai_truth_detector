import curses
import json
import requests
import textwrap

API_KEY = "sk-hc-v1-5296baa0916e4ec38c93f257dae9c11ce1ffbe60de064dae9ef0184a479afb34"
API_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"
MODEL = "google/gemini-3-flash-preview"

INVESTIGATORS = [
    {"name": "DETECTIVE NO. 1", "style": "good cop, empathetic but still manipulative, kind, establishes trust"},
    {"name": "DETECTIVE NO. 2", "style": "psychoanalyst, tries to make everything about trauma, lowkey weird, unsettling"},
    {"name": "DETECTIVE NO. 3", "style": "bad cop, threatening & manipulative, yelling, tries to take you down"},
    {"name": "DETECTIVE NO. 4", "style": "the impatient, tired, 'we can go this the easy way or we can go this hard way'."}
]

QUESTIONS_PER_COP = 5
TOTAL_ROUNDS = len(INVESTIGATORS) * QUESTIONS_PER_COP

# stupid hackclubisms TODO: make this work
HACK_CLUB_DICT = {
    "HCB": "HCB (Hack Club Bank ; non-profit finance system)",
    "Hack Club": "Hack Club (non-profit for coding clubs)",
    "William Daniel": "William Daniel (suspected murderer)", 
    "YSWS": "YSWS (You Ship, We Ship ; hackathon format)"
}

SYSTEM_PROMPT = f"""
You are a detective interrogating a suspect regarding a confession they made and making a judgement.
You must ask blunt, brief, and relevant questions, avoid being overly verbose.
Stick to your role as a detective (do NOT be extra and do NOT be corny) and try to get to the end of the situation.
Try to poke holes in the narrative and attempt to set traps that would catch blatant lies.

Rules:
- You are one of several detectives taking turns.
- Ask one question at a time.
- If the limit is reached, make a best guess.
Final output format:
FINAL ANSWER: TRUE or FALSE
Explanation: short explanation
Appropriate punishment: legal judgement
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
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
    
    h, w = stdscr.getmaxyx()

    # confession ui
    stdscr.clear()
    prompt = "CONFESS YOUR CRIME"
    py, px = center_print(stdscr, prompt, y_offset=-2, attr=curses.A_BOLD | curses.A_UNDERLINE)
    
    box_width = min(60, w - 4)
    box_x = (w - box_width) // 2
    box_y = py + 2
    
    stdscr.attron(curses.color_pair(4))
    stdscr.addstr(box_y, box_x, " " * box_width)
    stdscr.attroff(curses.color_pair(4))
    
    curses.echo()
    curses.curs_set(1)
    
    try:
        stdscr.attron(curses.color_pair(4))
        confession = stdscr.getstr(box_y, box_x + 1, box_width - 2).decode('utf-8')
        stdscr.attroff(curses.color_pair(4))
    except curses.error:
        return

    if not confession.strip():
        return

    curses.noecho()
    curses.curs_set(0)
    
    # interrogation loop
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"I confess: {confession}"}
    ]
    
    history = [("YOU", 2, confession)]
    questions_count = 0

    while True:
        stdscr.clear()
        
        # calculate which cop is active
        if questions_count < TOTAL_ROUNDS:
            cop_idx = questions_count // QUESTIONS_PER_COP
            cop = INVESTIGATORS[cop_idx]
            
            # format specific round info
            round_q = (questions_count % QUESTIONS_PER_COP) + 1
            label = f"{cop['name']} ({round_q}/{QUESTIONS_PER_COP})"
        else:
            label = "JUDGEMENT"

        header = f" INTERROGATION | {label} "
        stdscr.addstr(0, (w - len(header)) // 2, header, curses.A_REVERSE)
        
        current_y = h - 4
        for role, color, text in reversed(history):
            wrapper = textwrap.TextWrapper(width=w-4)
            lines = wrapper.wrap(text)
            
            if current_y - len(lines) < 1: break
                
            for line in reversed(lines):
                stdscr.addstr(current_y, 2, line)
                current_y -= 1
            
            stdscr.addstr(current_y, 2, f"{role}:", curses.color_pair(color) | curses.A_BOLD)
            current_y -= 2

        stdscr.refresh()

        # ai turn
        if len(history) % 2 != 0:
            stdscr.addstr(h-2, 2, "Thinking...", curses.color_pair(3) | curses.A_BLINK)
            stdscr.refresh()
            
            if questions_count < TOTAL_ROUNDS:
                cop_idx = questions_count // QUESTIONS_PER_COP
                cop = INVESTIGATORS[cop_idx]
                
                inject = f"Current Speaker: {cop['name']}. Attitude: {cop['style']}. This is question {(questions_count % QUESTIONS_PER_COP) + 1} of 5 for you."
                messages.append({"role": "system", "content": inject})
                
                response = query_llm(messages)
                history.append((cop['name'], 1, response))
                questions_count += 1
            else:
                messages.append({"role": "system", "content": "Limit reached. Provide FINAL ANSWER, Explanation, and Punishment."})
                response = query_llm(messages)
                history.append(("JUDGEMENT", 1, response))
            
            continue

        # end check
        last_msg = history[-1][2]
        if "FINAL ANSWER" in last_msg or questions_count > TOTAL_ROUNDS:
            stdscr.addstr(h-2, 2, "[CASE CLOSED] Press key to exit.", curses.A_BOLD | curses.A_REVERSE)
            stdscr.getch()
            break

        # user input
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
        
        # break with q
        if user_input.strip() == "q":
            break
            
        if not user_input.strip(): continue

        messages.append({"role": "assistant", "content": last_msg})
        messages.append({"role": "user", "content": user_input})
        history.append(("YOU", 2, user_input))

if __name__ == "__main__":
    curses.wrapper(main)