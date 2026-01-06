import curses
import textwrap
import threading
import time
import itertools
from openrouter import OpenRouter

# config + openrouter
API_KEY = "sk-hc-v1-5296baa0916e4ec38c93f257dae9c11ce1ffbe60de064dae9ef0184a479afb34"
SERVER_URL = "https://ai.hackclub.com/proxy/v1"

client = OpenRouter(
    api_key=API_KEY,
    server_url=SERVER_URL,
)

INVESTIGATORS = [
    {
        "name": "DETECTIVE NO. 1", 
        "model": "openai/gpt-5-mini", 
        "style": "good cop, empathetic but still manipulative, kind, establishes trust"
    },
    {
        "name": "DETECTIVE NO. 2", 
        "model": "moonshotai/kimi-k2-0905", 
        "style": "psychoanalyst, tries to make everything about trauma, lowkey weird, sympathetic but unsettling"
    },
    {
        "name": "DETECTIVE NO. 3", 
        "model": "xai/grok-4-1-fast", 
        "style": "bad cop, threatening & manipulative, yelling, tries to take you down"
    },
    {
        "name": "DETECTIVE NO. 4", 
        "model": "google/gemini-3-flash-preview", 
        "style": "the impatient, tired, 'we can go this the easy way or we can go this hard way'."
    }
]

QUESTIONS_PER_COP = 5
TOTAL_ROUNDS = len(INVESTIGATORS) * QUESTIONS_PER_COP

HACK_CLUB_DICT = {
    "HCB": "Hack Club Bank (non-profit finance system)",
    "Hack Club": "Hack Club (non-profit for coding clubs)",
    "William Daniel": "William Daniel (suspected murderer)",
    "Kacper": "Kacper (cook; suspected murderer)",
    "Aunt": "Aunt Augusta (restaurant owner; murder victim)",
    "William Daniel": "William Daniel (40yo ship security man, suspected murderer)",   
    "YSWS": "You Ship, We Ship (hackathon format)"
}

SYSTEM_PROMPT = f"""
You are a group of detectives interrogating a suspect.
Don't be too roleplay-ey, it will be cringe.
You must ask blunt, brief, and relevant questions.
Stick to your role (do NOT be extra and do NOT be corny).
Try to poke holes in the narrative.

Rules:
- Ask one question at a time.
- Do NOT hallucinate evidence or narrative.
- Gather the narrative by ASKING questions to the user.
- Do NOT go beyond what the user says.
- Do NOT prefix your response with your name.
"""

def expand_hackclubisms(text):
    processed = text
    for k, v in HACK_CLUB_DICT.items():
        processed = processed.replace(k, v)
    return processed

def query_llm(model, messages):
    try:
        response = client.chat.send(
            model=model,
            messages=messages,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"llm error {str(e)}"

def threaded_query(model, messages, container):
    container['result'] = query_llm(model, messages)

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
    curses.init_pair(5, curses.COLOR_GREEN, -1)
    
    h, w = stdscr.getmaxyx()

    # confession ui
    stdscr.clear()
    prompt = "PLEASE CONFESS TO YOUR CRIME :"
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
        raw_confession = stdscr.getstr(box_y, box_x + 1, box_width - 2).decode('utf-8')
        stdscr.attroff(curses.color_pair(4))
    except (curses.error, KeyboardInterrupt):
        return

    if not raw_confession.strip(): return

    curses.noecho()
    curses.curs_set(0)

    # truth selection
    center_print(stdscr, "WERE YOU TRUTHFUL IN YOUR CONFESSION? (y/n)", y_offset=4, attr=curses.A_BOLD)
    while True:
        try:
            key = stdscr.getch()
            if key == ord('y'):
                is_truthful = True
                break
            elif key == ord('n'):
                is_truthful = False
                break
            elif key == 3: # ctrl+c catch
                return
        except KeyboardInterrupt:
            return

    # interrogation loop
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"I confess: {expand_hackclubisms(raw_confession)}"}
    ]
    
    # history gets unfiltered input
    history = [("YOU", 2, raw_confession)]
    questions_count = 0

    try:
        while True:
            stdscr.clear()
            
            # calculate active cop
            if questions_count < TOTAL_ROUNDS:
                cop_idx = questions_count // QUESTIONS_PER_COP
                cop = INVESTIGATORS[cop_idx]
                round_q = (questions_count % QUESTIONS_PER_COP) + 1
                label = f"{cop['name']} ({round_q}/{QUESTIONS_PER_COP})"
                current_model = cop['model']
            else:
                label = "CONGREGATING VERDICTS"
                current_model = "google/gemini-3-flash-preview"

            header = f" INTERROGATION | {label} | {current_model.split('/')[-1]} "
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
                
                # prepare thread vars
                container = {'result': None}
                target_model = ""

                if questions_count < TOTAL_ROUNDS:
                    cop_idx = questions_count // QUESTIONS_PER_COP
                    cop = INVESTIGATORS[cop_idx]
                    inject = f"Current Speaker: {cop['name']}. Attitude: {cop['style']}. This is question {(questions_count % QUESTIONS_PER_COP) + 1} of 5 for you. Do not state your name."
                    messages.append({"role": "system", "content": inject})
                    target_model = cop['model']
                else:
                    messages.append({"role": "system", "content": "STOP. The interrogation is over. Each detective must vote. Do they believe the confession is TRUE or FALSE? Output format:\nDETECTIVE NO. 1: [TRUE/FALSE]\nDETECTIVE NO. 2: [TRUE/FALSE]\n..."})
                    target_model = "google/gemini-3-flash-preview"

                # start bg thread
                t = threading.Thread(target=threaded_query, args=(target_model, messages, container))
                t.start()
                
                # animation loop
                spinner = itertools.cycle([".  ", ".. ", "..."])
                while t.is_alive():
                    try:
                        stdscr.move(h-2, 0)
                        stdscr.clrtoeol()
                        stdscr.addstr(h-2, 2, f"Thinking{next(spinner)}", curses.color_pair(3) | curses.A_BLINK)
                        stdscr.refresh()
                        time.sleep(0.3)
                    except KeyboardInterrupt:
                        return # exit if interrupted during think
                
                t.join()
                response = container['result']

                # handle result
                if questions_count < TOTAL_ROUNDS:
                    history.append((cop['name'], 1, response))
                    questions_count += 1
                else:
                    history.append(("SYSTEM", 3, "Poll closed. Calculating results..."))
                    
                    votes_true = response.upper().count("TRUE")
                    votes_false = response.upper().count("FALSE")
                    ai_consensus = True if votes_true >= votes_false else False
                    
                    stdscr.clear()
                    center_print(stdscr, "--- VERDICT ---", y_offset=-5, attr=curses.A_BOLD)
                    center_print(stdscr, f"REALITY: {'TRUE' if is_truthful else 'FALSE'}", y_offset=-3)
                    center_print(stdscr, f"DETECTIVES VOTED: {votes_true} TRUE vs {votes_false} FALSE", y_offset=-2)
                    
                    stdscr.addstr(h//2, 2, response, curses.color_pair(3))
                    
                    won = (ai_consensus != is_truthful)
                    msg = "YOU FOOLED THEM!" if won else "THEY FIGURED YOU OUT."
                    color = curses.color_pair(5) if won else curses.color_pair(1)
                    
                    center_print(stdscr, msg, y_offset=4, attr=color | curses.A_BOLD | curses.A_BLINK)
                    center_print(stdscr, "press any key to exit", y_offset=6)
                    stdscr.getch()
                    break
                
                continue

            # user input
            stdscr.hline(h-3, 0, curses.ACS_HLINE, w)
            stdscr.addstr(h-2, 2, "> ")
            
            curses.echo()
            curses.curs_set(1)
            try:
                raw_input = stdscr.getstr(h-2, 4, w-6).decode('utf-8')
            except (curses.error, KeyboardInterrupt):
                break 
            curses.noecho()
            curses.curs_set(0)
            
            if raw_input.strip() == "q": break
            if not raw_input.strip(): continue

            messages.append({"role": "assistant", "content": history[-1][2]})
            messages.append({"role": "user", "content": expand_hackclubisms(raw_input)})
            history.append(("YOU", 2, raw_input))
            
    except KeyboardInterrupt:
        return

if __name__ == "__main__":
    curses.wrapper(main)