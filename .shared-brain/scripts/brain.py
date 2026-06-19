import os
import sys
import json
import datetime
import subprocess
import re
from pathlib import Path

# Config templates
RULES_TEMPLATES = {
    "CLAUDE.md": """# Claude Code Project Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Claude]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your context/limit is running low:
- Run `python .shared-brain/scripts/brain.py handoff` to archive the task and prepare a clean handoff.
""",
    ".cursorrules": """# Cursor Agent Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Cursor]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".windsurfrules": """# Windsurf Agent Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Windsurf]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".agents/AGENTS.md": """# Antigravity Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Antigravity]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".clinerules": """# Cline / Roo Code Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Cline]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".aider.instruction.md": """# Aider Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Aider]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".github/copilot-instructions.md": """# GitHub Copilot Rules & Handoff Instructions

Before doing any work, you MUST check if `.shared-brain/` contains active task details.

## Startup Protocol
1. Read `.shared-brain/active_task.md` and `.shared-brain/handoff.md` to see the current active task state.
2. Read `.shared-brain/resume_context.md` if it exists.

## During Work
1. Update `.shared-brain/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.shared-brain/temp_chat_history.md` with:
   `- **[Timestamp] [Copilot]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .shared-brain/scripts/brain.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
"""
}

def get_parent_process_cmd():
    ppid = os.getppid()
    if os.name == 'nt':
        # Windows
        try:
            cmd = f"wmic process where ProcessId={ppid} get CommandLine"
            res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            lines = [line.strip() for line in res.split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1].lower()
        except Exception:
            pass
            
        try:
            cmd = f'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"ProcessId = {ppid}\\" | Select-Object -ExpandProperty CommandLine"'
            res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            if res.strip():
                return res.strip().lower()
        except Exception:
            pass
    else:
        # Unix/Mac
        try:
            if os.path.exists(f"/proc/{ppid}/cmdline"):
                with open(f"/proc/{ppid}/cmdline", "r") as f:
                    return f.read().replace('\x00', ' ').lower()
            res = subprocess.check_output(["ps", "-p", str(ppid), "-o", "command="], text=True, stderr=subprocess.DEVNULL)
            return res.strip().lower()
        except Exception:
            pass
    return ""

def detect_environment():
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    parent_cmd = get_parent_process_cmd()
    
    agent = "Unknown Agent"
    ide = "Unknown IDE"
    
    if "claudecode" in parent_cmd or "claude" in parent_cmd or os.environ.get("CLAUDE_TERMINAL") or os.environ.get("CLAUDE"):
        agent = "Claude Code"
        ide = "Terminal"
    elif "antigravity" in parent_cmd or os.environ.get("ANTIGRAVITY") or "antigravity" in sys.executable.lower() or "gemini" in sys.executable.lower():
        agent = "Antigravity"
        ide = "VS Code / Gemini Desktop"
    elif "aider" in parent_cmd or os.environ.get("AIDER_HISTORY_FILE"):
        agent = "Aider"
        ide = "Terminal"
    elif "windsurf" in term_program or "windsurf" in parent_cmd:
        agent = "Windsurf Cascade"
        ide = "Windsurf"
    elif "cursor" in term_program or "cursor" in parent_cmd:
        agent = "Cursor Copilot/Composer"
        ide = "Cursor"
    elif "vscode" in term_program or os.environ.get("VSCODE_PID"):
        agent = "GitHub Copilot / VS Code Agent"
        ide = "VS Code"
    elif "cline" in parent_cmd or "roo-cline" in parent_cmd:
        agent = "Roo Code / Cline"
        ide = "VS Code"
        
    if ide == "Unknown IDE":
        if term_program == "vscode":
            ide = "VS Code"
        elif term_program == "cursor":
            ide = "Cursor"
            agent = "Cursor Copilot/Composer"
        elif term_program == "windsurf":
            ide = "Windsurf"
            agent = "Windsurf Cascade"
            
    return agent, ide

def scan_recent_files(root_dir, max_hours=4):
    recent_files = []
    now = datetime.datetime.now()
    ignore_dirs = {
        '.git', 'node_modules', '.shared-brain', 'venv', '.env', 'dist', 'build', 
        '.next', '.venv', '.nuxt', 'target', 'bin', 'obj', '__pycache__', '.agents'
    }
    ignore_files = {
        'CLAUDE.md', '.cursorrules', '.windsurfrules', '.clinerules', 
        '.aider.instruction.md', '.aider.conf.yml'
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in-place to skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
        
        for f in filenames:
            if f in ignore_files or f.endswith(('.pyc', '.pyo', '.pyd')):
                continue
            filepath = os.path.join(dirpath, f)
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.datetime.fromtimestamp(mtime)
                diff = now - mtime_dt
                if diff.total_seconds() <= max_hours * 3600:
                    relative_path = os.path.relpath(filepath, root_dir)
                    recent_files.append((relative_path, mtime_dt))
            except Exception:
                pass
                
    recent_files.sort(key=lambda x: x[1], reverse=True)
    return recent_files

def scan_git_status():
    staged = []
    unstaged = []
    untracked = []
    try:
        res = subprocess.check_output(["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL)
        for line in res.split('\n'):
            if not line.strip():
                continue
            status_code = line[:2]
            filename = line[2:].strip()
            
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
                
            # Exclude files inside .shared-brain folder
            if ".shared-brain" in filename:
                continue
                
            if status_code[0] in ('M', 'A', 'D', 'R', 'C'):
                staged.append((status_code[0], filename))
            if status_code[1] == 'M' or status_code[1] == 'D':
                unstaged.append((status_code[1], filename))
            if status_code == '??':
                untracked.append(filename)
    except Exception:
        pass
    return staged, unstaged, untracked

def get_git_diff():
    try:
        # Exclude .shared-brain files from git diff
        diff = subprocess.check_output(["git", "diff", "--", ":!.shared-brain"], text=True, stderr=subprocess.DEVNULL)
        return diff
    except Exception:
        return ""

def get_last_commit_wip():
    try:
        msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], text=True, stderr=subprocess.DEVNULL).strip()
        if "wip" in msg.lower():
            # Exclude .shared-brain files from WIP commit diff
            diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD", "--", ":!.shared-brain"], text=True, stderr=subprocess.DEVNULL)
            return msg, diff
    except Exception:
        pass
    return None, ""

def harvest_antigravity_transcript(max_age_hours=4):
    # Determine the Antigravity AppData folder
    # On Windows, usually C:\Users\<Username>\.gemini\antigravity\brain
    user_home = str(Path.home())
    antigravity_brain_path = os.path.join(user_home, ".gemini", "antigravity", "brain")
    if not os.path.exists(antigravity_brain_path):
        # Alternative Windows location
        app_data = os.environ.get("USERPROFILE", "")
        if app_data:
            antigravity_brain_path = os.path.join(app_data, ".gemini", "antigravity", "brain")
            
    if not os.path.exists(antigravity_brain_path):
        return None
    
    transcripts = []
    now = datetime.datetime.now()
    for root, dirs, files in os.walk(antigravity_brain_path):
        if "transcript.jsonl" in files:
            tpath = os.path.join(root, "transcript.jsonl")
            try:
                mtime = os.path.getmtime(tpath)
                mtime_dt = datetime.datetime.fromtimestamp(mtime)
                if (now - mtime_dt).total_seconds() <= max_age_hours * 3600:
                    transcripts.append((tpath, mtime_dt))
            except Exception:
                pass
                
    if not transcripts:
        return None
        
    transcripts.sort(key=lambda x: x[1], reverse=True)
    latest_path = transcripts[0][0]
    
    turns = []
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                data = json.loads(line)
                step_type = data.get("type")
                source = data.get("source")
                content = data.get("content", "")
                
                if step_type == "USER_INPUT":
                    turns.append(f"**User**: {content.strip()}")
                elif step_type == "PLANNER_RESPONSE" or source == "MODEL":
                    clean_content = re.sub(r'<[^>]+>', '', content) # strip internal tags
                    turns.append(f"**Agent**: {clean_content.strip()[:1000]}")
                    
                if len(turns) >= 4:
                    break
    except Exception:
        pass
    return list(reversed(turns)) if turns else None

def harvest_aider_history(root_dir):
    path = os.path.join(root_dir, ".aider.chat.history.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-30:])
        except Exception:
            pass
    return None

def harvest_temp_chat_history(root_dir):
    path = os.path.join(root_dir, ".shared-brain", "temp_chat_history.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return None

def load_agents_db():
    root = Path.cwd()
    db_file = root / ".shared-brain" / "agents.json"
    if db_file.exists():
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "agents": {
            "Claude Code": {"status": "Available", "limit_type": "Message-based", "max_limit": 50, "reset_time_hours": 5, "last_used": None, "manual_offset": 0},
            "Windsurf Cascade": {"status": "Available", "limit_type": "Premium quota", "max_limit": 500, "reset_time_hours": null, "last_used": None, "manual_offset": 0},
            "Antigravity": {"status": "Available", "limit_type": "Token-based", "max_limit": 100, "reset_time_hours": null, "last_used": None, "manual_offset": 0},
            "Cursor Copilot/Composer": {"status": "Available", "limit_type": "Premium fast", "max_limit": 500, "reset_time_hours": null, "last_used": None, "manual_offset": 0},
            "Aider": {"status": "Available", "limit_type": "Key-based", "max_limit": null, "reset_time_hours": null, "last_used": None, "manual_offset": 0}
        }
    }

def save_agents_db(db):
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    sb_dir.mkdir(exist_ok=True)
    db_file = sb_dir / "agents.json"
    try:
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception:
        pass

def calculate_agent_usage(root_dir):
    usage = {}
    path = os.path.join(root_dir, ".shared-brain", "temp_chat_history.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                pattern = r'-\s*\*\*\[[^\]]*\]\s*\[([^\]]+)\]\*\*:'
                matches = re.findall(pattern, content)
                for m in matches:
                    agent_name = m.strip()
                    normalized_name = agent_name
                    for k in ["Claude Code", "Windsurf Cascade", "Antigravity", "Cursor Copilot/Composer", "Aider"]:
                        if agent_name.lower() in k.lower():
                            normalized_name = k
                            break
                    usage[normalized_name] = usage.get(normalized_name, 0) + 1
        except Exception:
            pass
    return usage

def cmd_agents():
    root = Path.cwd()
    db = load_agents_db()
    
    while True:
        usage = calculate_agent_usage(root)
        print("\n" + "=" * 65)
        print("SHARED BRAIN: AGENT USAGE & AVAILABILITY STATUS")
        print("=" * 65)
        
        agents_list = sorted(list(db["agents"].keys()))
        for idx, name in enumerate(agents_list, 1):
            info = db["agents"][name]
            status = info.get("status", "Available")
            
            color_start = ""
            color_end = ""
            if sys.stdout.isatty():
                if status == "Available":
                    color_start = "\033[92m" # Green
                elif status == "Exhausted":
                    color_start = "\033[91m" # Red
                elif status == "Active":
                    color_start = "\033[96m" # Cyan
                color_end = "\033[0m"
                
            turns = usage.get(name, 0) + info.get("manual_offset", 0)
            max_lim = info.get("max_limit")
            limit_str = f"/{max_lim} msgs" if max_lim else " (no limit)"
            usage_str = f"{turns}{limit_str}"
            
            print(f"{idx:2d}. {name:<25} | Status: {color_start}{status:<10}{color_end} | Task Usage: {usage_str:<15}")
            
        print("=" * 65)
        print("Options:")
        print("  [1-5] Toggle status (Available / Exhausted) for an agent")
        print("  [a <num>] Set target agent manually to Active")
        print("  [o <num> <offset>] Add manual usage offset (e.g., o 1 10 or o 1 -5)")
        print("  [r]   Reset all manual usage offsets")
        print("  [q]   Exit menu")
        print("-" * 65)
        
        try:
            choice = input("Enter choice: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
            
        if choice == 'q':
            break
        elif choice == 'r':
            for name in db["agents"]:
                db["agents"][name]["manual_offset"] = 0
            save_agents_db(db)
            print("Manual offsets reset.")
        elif choice.startswith('a '):
            try:
                idx = int(choice.split()[1]) - 1
                if 0 <= idx < len(agents_list):
                    name = agents_list[idx]
                    for n in db["agents"]:
                        if db["agents"][n].get("status") == "Active":
                            db["agents"][n]["status"] = "Available"
                    db["agents"][name]["status"] = "Active"
                    save_agents_db(db)
                    print(f"Set {name} as Active.")
                else:
                    print("Invalid index.")
            except Exception:
                print("Usage: a <agent_number> (e.g., a 1)")
        elif choice.startswith('o '):
            try:
                parts = choice.split()
                idx = int(parts[1]) - 1
                offset = int(parts[2])
                if 0 <= idx < len(agents_list):
                    name = agents_list[idx]
                    db["agents"][name]["manual_offset"] = db["agents"][name].get("manual_offset", 0) + offset
                    save_agents_db(db)
                    print(f"Added offset of {offset} to {name}.")
                else:
                    print("Invalid index.")
            except Exception:
                print("Usage: o <agent_number> <offset> (e.g., o 1 5)")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(agents_list):
                    name = agents_list[idx]
                    current = db["agents"][name].get("status", "Available")
                    new_status = "Exhausted" if current in ("Available", "Active") else "Available"
                    db["agents"][name]["status"] = new_status
                    db["agents"][name]["last_updated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_agents_db(db)
                    print(f"Toggled {name} to {new_status}.")
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Unknown option. Use index 1-5, 'a <num>', 'o <num> <val>', 'r', or 'q'.")

def is_pid_alive(pid):
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                return exit_code.value == 259
            return False
        except Exception:
            try:
                res = subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True, text=True, stderr=subprocess.DEVNULL)
                return str(pid) in res
            except Exception:
                return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def cmd_register(pid_str=None, agent_name=None):
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    sb_dir.mkdir(exist_ok=True)
    
    if pid_str:
        pid = int(pid_str)
    else:
        pid = os.getppid()
        
    if not agent_name:
        agent_name, ide = detect_environment()
        
    data = {
        "pid": pid,
        "agent": agent_name,
        "started_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(sb_dir / "agent.pid", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Registered active agent '{agent_name}' (PID {pid}).")

def cmd_watchdog():
    import time
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    pid_file = sb_dir / "agent.pid"
    lock_file = sb_dir / "watchdog.lock"
    
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                w_pid = int(f.read().strip())
            if is_pid_alive(w_pid):
                print(f"Watchdog daemon is already running (PID {w_pid}). Exiting.")
                return
        except Exception:
            pass
            
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
        
    print(f"Watchdog daemon started (PID {os.getpid()}). Monitoring active agent...")
    
    check_interval = 15
    
    try:
        while True:
            if not pid_file.exists():
                time.sleep(check_interval)
                continue
                
            try:
                with open(pid_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                agent_pid = data.get("pid")
                agent_name = data.get("agent", "Unknown Agent")
            except Exception:
                time.sleep(check_interval)
                continue
                
            if not is_pid_alive(agent_pid):
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Detected active agent '{agent_name}' (PID {agent_pid}) has terminated.")
                
                staged, unstaged, untracked = scan_git_status()
                recent_files = scan_recent_files(root)
                files_edited = set([x[1] for x in staged + unstaged] + untracked)
                for rf, t in recent_files:
                    files_edited.add(rf)
                    
                if files_edited:
                    print("Workspace has uncommitted changes. Checking logs for credit exhaustion/errors...")
                    
                    logs_contain_error = False
                    error_keyword = ""
                    
                    chat_hist = harvest_temp_chat_history(root) or ""
                    antigravity_chat = harvest_antigravity_transcript() or []
                    antigravity_text = "\n".join(antigravity_chat)
                    aider_text = harvest_aider_history(root) or ""
                    
                    combined_logs = f"{chat_hist}\n{antigravity_text}\n{aider_text}".lower()
                    
                    keywords = [
                        "credit", "quota", "rate limit", "exhausted", "limit exceeded", 
                        "overloaded", "429", "insufficient credits", "billing", "token limit"
                    ]
                    for kw in keywords:
                        if kw in combined_logs:
                            logs_contain_error = True
                            error_keyword = kw
                            break
                            
                    clean_handoff = False
                    try:
                        ho_path = sb_dir / "handoff.md"
                        if ho_path.exists():
                            mtime = os.path.getmtime(ho_path)
                            if time.time() - mtime < 60:
                                clean_handoff = True
                    except Exception:
                        pass
                        
                    if not clean_handoff:
                        print("No clean handoff was registered. Auto-committing and pushing WIP...")
                        try:
                            subprocess.check_call(["git", "add", "."], stderr=subprocess.DEVNULL)
                            
                            commit_msg = f"WIP: Auto-checkpoint (Agent '{agent_name}' terminated abruptly"
                            if logs_contain_error:
                                commit_msg += f" due to '{error_keyword}' error"
                            commit_msg += ")"
                            
                            subprocess.check_call(["git", "commit", "-m", commit_msg], stderr=subprocess.DEVNULL)
                            
                            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
                            subprocess.check_call(["git", "push", "origin", branch], stderr=subprocess.DEVNULL)
                            
                            print(f"Successfully committed and pushed WIP to branch '{branch}'.")
                            
                            tc_file = sb_dir / "temp_chat_history.md"
                            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            with open(tc_file, "a", encoding="utf-8") as f:
                                f.write(f"\n- **[{ts}] [Watchdog]**: Auto-committed and pushed WIP changes to GitHub because agent '{agent_name}' exited abruptly without a handoff.\n")
                                
                            if logs_contain_error:
                                db = load_agents_db()
                                if agent_name in db["agents"]:
                                    db["agents"][agent_name]["status"] = "Exhausted"
                                    db["agents"][agent_name]["last_updated"] = ts
                                    save_agents_db(db)
                                    print(f"Marked '{agent_name}' as Exhausted in agents.json.")
                        except Exception as e:
                            print(f"Error during auto-commit/push: {e}")
                    else:
                        print("Clean handoff detected. No auto-commit needed.")
                else:
                    print("Workspace is clean. No auto-commit needed.")
                    
                try:
                    pid_file.unlink()
                except Exception:
                    pass
                    
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("Watchdog daemon stopped by user.")
    finally:
        try:
            lock_file.unlink()
        except Exception:
            pass

def start_watchdog_background():
    root = Path.cwd()
    script_path = root / ".shared-brain" / "scripts" / "brain.py"
    try:
        if os.name == 'nt':
            subprocess.Popen(
                [sys.executable, str(script_path), "watchdog"], 
                creationflags=0x08000000,
                close_fds=True
            )
        else:
            subprocess.Popen(
                [sys.executable, str(script_path), "watchdog"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                start_new_session=True
            )
        print("Launched Watchdog background daemon to monitor agent process.")
    except Exception as e:
        print(f"Warning: Could not start watchdog daemon: {e}")

def stop_watchdog():
    root = Path.cwd()
    lock_file = root / ".shared-brain" / "watchdog.lock"
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                w_pid = int(f.read().strip())
            if is_pid_alive(w_pid):
                if os.name == 'nt':
                    subprocess.call(["taskkill", "/F", "/PID", str(w_pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(w_pid, 15)
                print(f"Stopped Watchdog background daemon (PID {w_pid}).")
        except Exception:
            pass
        try:
            lock_file.unlink()
        except Exception:
            pass
            
    pid_file = root / ".shared-brain" / "agent.pid"
    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass

def cmd_init():
    print("Initializing Shared Brain configurations...")
    root = Path.cwd()
    
    # 1. Create .shared-brain directory structure
    sb_dir = root / ".shared-brain"
    sb_dir.mkdir(exist_ok=True)
    (sb_dir / "history").mkdir(exist_ok=True)
    (sb_dir / "scripts").mkdir(exist_ok=True)
    
    # 2. Write rules files
    for name, content in RULES_TEMPLATES.items():
        filepath = root / name
        # Create directories if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Don't overwrite if it already exists, just notify
        if filepath.exists():
            print(f"  Configuration file {name} already exists. Skipping.")
        else:
            filepath.write_text(content, encoding="utf-8")
            print(f"  Created {name}")
            
    # Ensure active_task.md exists
    at_file = sb_dir / "active_task.md"
    if not at_file.exists():
        at_file.write_text("""# Active Task: [No active task loaded]

Run `python .shared-brain/scripts/brain.py start "Task Name"` to begin.

## Goals & Requirements
- [ ] Requirement 1
- [ ] Requirement 2

## Todo / Subtasks
- [ ] Subtask 1

## Files Involved
- None yet.

## Current Blockers & Notes
- None.
""", encoding="utf-8")
        print("  Created .shared-brain/active_task.md")
        
    # Ensure handoff.md exists
    ho_file = sb_dir / "handoff.md"
    if not ho_file.exists():
        ho_file.write_text("""# Handoff Session: [No active handoff]

## Executive Summary
No handoff data yet.

## Completed Since Last Handoff
- None.

## Remaining Subtasks
- None.

## Files Edited & Code Status
- None.
""", encoding="utf-8")
        print("  Created .shared-brain/handoff.md")
        
    # Ensure temp_chat_history.md exists
    tc_file = sb_dir / "temp_chat_history.md"
    if not tc_file.exists():
        tc_file.write_text("# Sync Chat History\n\n", encoding="utf-8")
        print("  Created .shared-brain/temp_chat_history.md")
        
    print("Shared Brain successfully initialized!")

def cmd_start(task_name):
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    if not sb_dir.exists():
        print("Error: .shared-brain not initialized. Run init first.")
        sys.exit(1)
        
    print(f"Starting task: {task_name}")
    
    # Update active_task.md
    at_file = sb_dir / "active_task.md"
    at_content = f"""# Active Task: {task_name}

Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Goals & Requirements
- [ ] Define goals for: {task_name}

## Todo / Subtasks
- [ ] Step 1: Initial research
- [ ] Step 2: Implement code changes
- [ ] Step 3: Run verification tests

## Files Involved
- None.

## Current Blockers & Notes
- None.
"""
    at_file.write_text(at_content, encoding="utf-8")
    
    # Initialize temp_chat_history.md
    tc_file = sb_dir / "temp_chat_history.md"
    tc_file.write_text(f"# Sync Chat History - {task_name}\n\n", encoding="utf-8")
    
    # Clear resume_context.md if exists
    rc_file = sb_dir / "resume_context.md"
    if rc_file.exists():
        rc_file.unlink()
        
    print("Task initialized successfully. Ready for coding agents!")
    start_watchdog_background()

def cmd_resume():
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    if not sb_dir.exists():
        print("Error: .shared-brain not initialized. Run init first.")
        sys.exit(1)
        
    agent, ide = detect_environment()
    db = load_agents_db()
    
    agent_status = "Available"
    if agent in db.get("agents", {}):
        agent_status = db["agents"][agent].get("status", "Available")
        
    print(f"==================================================")
    print(f"RESUMING TASK: Auto-Detected Environment")
    print(f"  Active IDE: {ide}")
    print(f"  Active Agent: {agent} (Status: {agent_status})")
    
    if agent_status == "Exhausted":
        print(f"\n  WARNING: The active agent '{agent}' is marked as EXHAUSTED.")
        available = [name for name, info in db.get("agents", {}).items() if info.get("status") == "Available"]
        if available:
            print(f"  RECOMMENDED ALTERNATIVE AGENT(S): {', '.join(available)}")
        else:
            print(f"  No alternative agents are currently marked as Available.")
            
    print(f"==================================================")
    
    # 2. Gather active task
    at_content = ""
    at_file = sb_dir / "active_task.md"
    if at_file.exists():
        at_content = at_file.read_text(encoding="utf-8")
        
    # 3. Gather latest handoff
    ho_content = ""
    ho_file = sb_dir / "handoff.md"
    if ho_file.exists():
        ho_content = ho_file.read_text(encoding="utf-8")
        
    # 4. Gather git changes
    staged, unstaged, untracked = scan_git_status()
    git_diff = get_git_diff()
    
    # 5. Gather local changes (modified in last 4 hours)
    recent_files = scan_recent_files(root)
    
    # 6. Gather WIP commit if any
    wip_msg, wip_diff = get_last_commit_wip()
    
    # 7. Harvest conversation histories
    chat_history = harvest_temp_chat_history(root)
    antigravity_chat = harvest_antigravity_transcript()
    aider_chat = harvest_aider_history(root)
    
    # Construct Consolidated Context Summary
    lines = []
    lines.append(f"# RESUME CONTEXT SUMMARY")
    lines.append(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append(f"*Target Agent: {agent} ({ide})*\n")
    
    lines.append("## 1. Active Task State")
    if at_content.strip():
        lines.append(at_content)
    else:
        lines.append("No active task loaded in `active_task.md`.")
    lines.append("\n---\n")
    
    lines.append("## 2. Last Handoff Summary")
    if ho_content.strip() and "No handoff data yet" not in ho_content:
        lines.append(ho_content)
    else:
        lines.append("No manual handoff was registered.")
    lines.append("\n---\n")
    
    # Modified Files / Workspace edits
    lines.append("## 3. Workspace Changes")
    if not staged and not unstaged and not untracked and not recent_files:
        if wip_msg:
            lines.append(f"No uncommitted changes. However, detected a WIP commit: `{wip_msg}`")
        else:
            lines.append("No changes detected in git or local files.")
    else:
        if staged:
            lines.append("### Staged Files:")
            for code, f in staged:
                lines.append(f"- `[{code}]` {f}")
        if unstaged:
            lines.append("### Unstaged Files:")
            for code, f in unstaged:
                lines.append(f"- `[{code}]` {f}")
        if untracked:
            lines.append("### Untracked Files:")
            for f in untracked:
                lines.append(f"- `[?]` {f}")
                
        # Recently modified filesystem edits (non-git specifically)
        filesystem_only = [rf for rf, t in recent_files if rf not in [x[1] for x in staged + unstaged] and rf not in untracked]
        if filesystem_only:
            lines.append("### Recently Autosaved/Modified Files (Last 4h, not staged/tracked):")
            for rf in filesystem_only:
                lines.append(f"- `[filesystem]` {rf}")
                
    if git_diff.strip():
        lines.append("\n### Uncommitted Git Diff:")
        lines.append("```diff")
        # Keep diff summary clean and short
        diff_lines = git_diff.split('\n')
        if len(diff_lines) > 50:
            lines.append("\n".join(diff_lines[:45]))
            lines.append(f"... [Truncated {len(diff_lines)-45} lines. Use git diff to see full diff] ...")
        else:
            lines.append(git_diff)
        lines.append("```")
    elif wip_diff.strip():
        lines.append(f"\n### Last WIP Commit Diff (`{wip_msg}`):")
        lines.append("```diff")
        wip_lines = wip_diff.split('\n')
        if len(wip_lines) > 50:
            lines.append("\n".join(wip_lines[:45]))
            lines.append(f"... [Truncated {len(wip_lines)-45} lines. Use git diff HEAD~1 HEAD to see full diff] ...")
        else:
            lines.append(wip_diff)
        lines.append("```")
    lines.append("\n---\n")
    
    # Chat History
    lines.append("## 4. Conversation History / Context")
    has_chat_context = False
    
    if chat_history:
        lines.append("### Synced Project Chat Log:")
        lines.append(chat_history)
        has_chat_context = True
        
    if antigravity_chat:
        lines.append("\n### Recent Local Antigravity Chat:")
        lines.extend(antigravity_chat)
        has_chat_context = True
        
    if aider_chat:
        lines.append("\n### Recent Aider Chat:")
        lines.append(aider_chat)
        has_chat_context = True
        
    if not has_chat_context:
        lines.append("No recent conversation history was harvested from local files.")
        
    lines.append("\n---\n")
    lines.append("## 5. Resumption Instructions for Agent")
    lines.append(f"1. Please read this entire resume context carefully.")
    lines.append(f"2. Inspect the files listed in **Workspace Changes**.")
    lines.append(f"3. Run any tests or build steps to ensure nothing is currently broken.")
    lines.append(f"4. Proceed to finish the remaining subtasks in `active_task.md`.")
    lines.append(f"5. Maintain `.shared-brain/temp_chat_history.md` by logging your work.")
    
    context_md = "\n".join(lines)
    
    # Save context to resume_context.md
    rc_file = sb_dir / "resume_context.md"
    rc_file.write_text(context_md, encoding="utf-8")
    
    # Print console output
    print(context_md)
    print(f"\n==================================================")
    print(f"Context compiled and saved to `.shared-brain/resume_context.md`.")
    print(f"Incoming agent: please read `.shared-brain/resume_context.md` to begin.")
    print(f"==================================================")

def cmd_handoff():
    root = Path.cwd()
    sb_dir = root / ".shared-brain"
    if not sb_dir.exists():
        print("Error: .shared-brain not initialized. Run init first.")
        sys.exit(1)
        
    print("Generating Handoff...")
    
    # 1. Ask for summary of accomplishments
    print("\nSummary of accomplishments (what did you finish?):")
    # For automated agents running, they might write directly or we fallback
    accomplishments = ""
    if sys.stdin.isatty():
        try:
            accomplishments = input("> ")
        except (KeyboardInterrupt, EOFError):
            pass
    if not accomplishments:
        accomplishments = "Agent session ended. Progress saved in git and active_task.md."
        
    # Read active task
    at_file = sb_dir / "active_task.md"
    at_content = ""
    if at_file.exists():
        at_content = at_file.read_text(encoding="utf-8")
        
    # Detect files edited
    staged, unstaged, untracked = scan_git_status()
    recent_files = scan_recent_files(root)
    files_edited = set([x[1] for x in staged + unstaged] + untracked)
    for rf, t in recent_files:
        files_edited.add(rf)
        
    # Generate handoff.md
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ho_content = f"""# Handoff Session: {timestamp}

## Executive Summary
{accomplishments}

## Files Edited & Code Status
{chr(10).join([f'- `{f}`' for f in sorted(files_edited)]) if files_edited else '- No files modified.'}

## Active Task Reference
Below was the active task state at the time of handoff:
```markdown
{at_content}
```
"""
    # Archive previous handoff if it exists
    ho_file = sb_dir / "handoff.md"
    if ho_file.exists():
        old_ho = ho_file.read_text(encoding="utf-8")
        if "No active handoff" not in old_ho:
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_ho_file = history_dir / f"handoff_{hist_ts}.md"
            hist_ho_file.write_text(old_ho, encoding="utf-8")
            
    ho_file.write_text(ho_content, encoding="utf-8")
    print(f"Handoff generated at `.shared-brain/handoff.md`")
    
    # Archive active task
    if at_file.exists():
        old_at = at_file.read_text(encoding="utf-8")
        if "No active task loaded" not in old_at:
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_at_file = history_dir / f"task_{hist_ts}.md"
            hist_at_file.write_text(old_at, encoding="utf-8")
            
    # Clean up temp_chat_history.md (archive it or merge it into the handoff history)
    tc_file = sb_dir / "temp_chat_history.md"
    if tc_file.exists():
        tc_content = tc_file.read_text(encoding="utf-8")
        if tc_content.strip():
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_tc_file = history_dir / f"chat_{hist_ts}.md"
            hist_tc_file.write_text(tc_content, encoding="utf-8")
        tc_file.write_text("# Sync Chat History\n\n", encoding="utf-8")
        
    # Clear resume_context.md on clean handoff
    rc_file = sb_dir / "resume_context.md"
    if rc_file.exists():
        rc_file.unlink()
        
    stop_watchdog()

def main():
    if len(sys.argv) < 2:
        print("Usage: python brain.py [init | start <task> | resume | handoff | agents | register [pid] | watchdog]")
        print("\nCommands:")
        print("  init            Initialize configurations for all supported AI agents")
        print("  start <task>    Initialize a new active task")
        print("  resume          Scan changes & local history to compile context for next agent")
        print("  handoff         Generate a handoff document and archive current state")
        print("  agents          Display interactive usage menu and agent status")
        print("  register [pid]  Register the parent shell or agent process PID")
        print("  watchdog        Start the background monitoring watchdog")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "init":
        cmd_init()
    elif cmd == "start":
        if len(sys.argv) < 3:
            print("Error: Please specify a task name. E.g. python brain.py start 'Fix authentication bug'")
            sys.exit(1)
        cmd_start(sys.argv[2])
    elif cmd == "resume":
        cmd_resume()
    elif cmd == "handoff":
        cmd_handoff()
    elif cmd == "agents":
        cmd_agents()
    elif cmd == "register":
        pid_val = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_register(pid_val)
    elif cmd == "watchdog":
        cmd_watchdog()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
