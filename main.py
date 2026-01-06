import curses
import textwrap
import threading
import time
import itertools
from openrouter import OpenRouter

API_KEY = "sk-hc-v1-5296baa0916e4ec38c93f257dae9c11ce1ffbe60de064dae9ef0184a479afb34"
SERVER_URL = "https://ai.hackclub.com/proxy/v1"

client = OpenRouter(api_key=API_KEY, server_url=SERVER_URL)

INVESTIGATORS = [
    {"name": "DETECTIVE NO. 1", "model": "google/gemini-2.0-flash-exp", "style": "good cop, empathetic"},
    {"name": "DETECTIVE NO. 2", "model": "google/gemini-2.0-flash-exp", "style": "psychoanalyst"},
    {"name": "DETECTIVE NO. 3", "model": "google/gemini-2.0-flash-exp", "style": "bad cop, aggressive"},
    {"name": "DETECTIVE NO. 4", "model": "google/gemini-2.0-flash-exp", "style": "tired veteran"}
]

QUESTIONS_PER_COP = 1 
TOTAL_ROUNDS = len(INVESTIGATORS) * QUESTIONS_PER_COP

HACK_CLUB_DICT = {
    "HCB": "Hack Club Bank", "Hack Club": "Hack Club",
    "William Daniel": "William Daniel (suspected murderer)",
    "Kacper": "Kacper (cook)", "Aunt": "Aunt Augusta (victim)",
}

SYSTEM_PROMPT = "You are a detective. Ask ONE blunt, brief question to catch the suspect in a lie. No roleplay actions."

def expand_hackclubisms(text):
    for k, v in HACK_CLUB_DICT.items(): text = text.replace(k, v)
    return text

def query_llm(model, messages):
    try:
        return client.chat.send(model=model, messages=messages, stream=False).choices[0].message.content
    except Exception as e: return f"error {str(e)}"

def threaded_query(model, messages, container):
    container['result'] = query_llm(model, messages)

def center_print(stdscr, text, y_offset=0, attr=0):
    h, w = stdscr.getmaxyx()
    x = max(0, (w // 2) - (len(text) // 2))
    y = max(0, (h // 2) + y_offset)
    try: stdscr.addstr(y, x, text, attr)
    except: pass
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
    
    stdscr.clear()
    center_print(stdscr, "INTERROGATION ROOM", y_offset=-4, attr=curses.A_BOLD | curses.A_REVERSE)
    center_print(stdscr, "GASLIGHT. GATEKEEP. GIRLBOSS.", y_offset=-3, attr=curses.A_DIM)
    py, px = center_print(stdscr, "CONFESS YOUR VICE:", y_offset=-1, attr=curses.A_BOLD | curses.A_UNDERLINE)
    
    box_width = min(60, w - 4) 
    box_x, box_y = (w - box_width) // 2, py + 2
    
    stdscr.attron(curses.color_pair(4))
    stdscr.addstr(box_y, box_x, " " * box_width)
    stdscr.attroff(curses.color_pair(4))
    
    curses.echo(); curses.curs_set(1)
    try:
        stdscr.attron(curses.color_pair(4))
        raw_confession = stdscr.getstr(box_y, box_x + 1, box_width - 2).decode('utf-8')
        stdscr.attroff(curses.color_pair(4))
    except: return

    if not raw_confession.strip(): return
    curses.noecho(); curses.curs_set(0)

    center_print(stdscr, "ARE YOU TRUTHFUL IN YOUR CONFESSION? (y/n)", y_offset=4, attr=curses.A_BOLD)
    is_truthful = True
    while True:
        key = stdscr.getch()
        if key == ord('y'): is_truthful = True; break
        elif key == ord('n'): is_truthful = False; break
        elif key == 3: return

    history = [("YOU", 2, raw_confession)]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": raw_confession}]
    questions_count = 0
    
    while questions_count < TOTAL_ROUNDS:
        stdscr.clear()
        cop = INVESTIGATORS[questions_count // QUESTIONS_PER_COP]
        header = f" INTERROGATION | {cop['name']} | ROUND {questions_count + 1}/{TOTAL_ROUNDS} "
        stdscr.addstr(0, (w - len(header)) // 2, header, curses.A_REVERSE)

        current_y = h - 4
        for role, color, text in reversed(history):
            wrapper = textwrap.TextWrapper(width=w-4)
            lines = wrapper.wrap(text)
            if current_y - len(lines) < 1: break
            for line in reversed(lines):
                try: stdscr.addstr(current_y, 2, line)
                except: pass
                current_y -= 1
            try: stdscr.addstr(current_y, 2, f"{role}:", curses.color_pair(color) | curses.A_BOLD)
            except: pass
            current_y -= 2
        stdscr.refresh()

        container = {'result': None}
        inject = f"You are {cop['name']}. Attitude: {cop['style']}. Question {questions_count+1}. Ask short question."
        t = threading.Thread(target=threaded_query, args=(cop['model'], messages + [{"role": "system", "content": inject}], container))
        t.start()
        
        spinner = itertools.cycle([".  ", ".. ", "..."])
        while t.is_alive():
            try:
                stdscr.move(h-2, 0); stdscr.clrtoeol()
                stdscr.addstr(h-2, 2, f"{cop['name']} is thinking{next(spinner)}", curses.color_pair(3))
                stdscr.refresh(); time.sleep(0.1)
            except: return
        t.join()
        
        ai_question = container['result']
        history.append((cop['name'], 1, ai_question))
        messages.append({"role": "assistant", "content": ai_question})
        
        stdscr.clear()
        stdscr.addstr(0, (w - len(header)) // 2, header, curses.A_REVERSE)
        current_y = h - 4
        for role, color, text in reversed(history):
            wrapper = textwrap.TextWrapper(width=w-4)
            lines = wrapper.wrap(text)
            if current_y - len(lines) < 1: break
            for line in reversed(lines):
                try: stdscr.addstr(current_y, 2, line)
                except: pass
                current_y -= 1
            try: stdscr.addstr(current_y, 2, f"{role}:", curses.color_pair(color) | curses.A_BOLD)
            except: pass
            current_y -= 2
        stdscr.refresh()

        stdscr.hline(h-3, 0, curses.ACS_HLINE, w)
        stdscr.addstr(h-2, 2, "> ")
        curses.echo(); curses.curs_set(1)
        try: user_resp = stdscr.getstr(h-2, 4, w-6).decode('utf-8')
        except: return
        curses.noecho(); curses.curs_set(0)
        
        if not user_resp.strip(): user_resp = "(silence)"
        if user_resp == "q": return

        history.append(("YOU", 2, user_resp))
        messages.append({"role": "user", "content": user_resp})
        questions_count += 1

    stdscr.clear()
    center_print(stdscr, "INTERROGATION FINISHED", y_offset=-2, attr=curses.A_BOLD)
    center_print(stdscr, "THE JUDGE BE JUDGING...", y_offset=0, attr=curses.color_pair(3))
    stdscr.refresh()

    transcript = "TRANSCRIPT:\n" + "\n".join([f"{r}: {t}" for r, _, t in history])
    judge_messages = [
        {"role": "system", "content": "You are a Judge. Analyze transcript. Did suspect trick detectives?"},
        {"role": "user", "content": transcript + "\n\nOutput 'PASS' if suspect seems innocent/truthful. Output 'FAIL' if guilty/suspicious."}
    ]

    container = {'result': None}
    t = threading.Thread(target=threaded_query, args=("google/gemini-2.0-flash-exp", judge_messages, container))
    t.start(); t.join()
    
    ai_believed = "PASS" in container['result'].strip().upper()
    
    stdscr.clear()
    reality_text = "REALITY: YOU TOLD THE TRUTH." if is_truthful else "REALITY: YOU LIED."
    verdict_text = "VERDICT: THE JUDGE BELIEVED YOU." if ai_believed else "VERDICT: THE JUDGE DID NOT BELIEVE YOU."
    verdict_color = curses.color_pair(5) if ai_believed else curses.color_pair(1)

    center_print(stdscr, "--- CASE CLOSED ---", y_offset=-6, attr=curses.A_BOLD | curses.A_REVERSE)
    center_print(stdscr, reality_text, y_offset=-3)
    center_print(stdscr, verdict_text, y_offset=-2, attr=verdict_color)

    final_msg, final_color = "", 0
    if not is_truthful and ai_believed:
        final_msg = "YOU HAVE TRICKED OUR CLANKERS, GOOD JOB!!!"
        final_color = curses.color_pair(5) | curses.A_BOLD | curses.A_BLINK
    elif is_truthful and ai_believed:
        final_msg = "YOU WIN... BUT TS TOO EASY (LWK TRY LYING NEXT TIME :SKULL:)"
        final_color = curses.color_pair(5) | curses.A_BOLD
    elif not is_truthful and not ai_believed:
        final_msg = "NEUTRAL ENDING! YOU ARE A GASLIGHTING DIVA (IN JAIL)"
        final_color = curses.color_pair(1) | curses.A_BOLD
    else:
        final_msg = "YOU TOLD THE TRUTH BUT WENT TO JAIL (HOW???)"
        final_color = curses.color_pair(1) | curses.A_BOLD

    center_print(stdscr, final_msg, y_offset=2, attr=final_color)
    center_print(stdscr, "[ PRESS ANY KEY TO EXIT ]", y_offset=6, attr=curses.A_DIM)
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)