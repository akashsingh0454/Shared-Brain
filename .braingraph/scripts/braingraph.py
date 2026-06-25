import os
import sys
import json
import datetime
import subprocess
import re
from pathlib import Path
import urllib.parse

# Config templates
RULES_TEMPLATES = {
    "CLAUDE.md": """# Claude Code Project Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Claude]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your context/limit is running low:
- Run `python .braingraph/scripts/braingraph.py handoff` to archive the task and prepare a clean handoff.
""",
    ".cursorrules": """# Cursor Agent Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Cursor]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".windsurfrules": """# Windsurf Agent Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Windsurf]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".agents/AGENTS.md": """# Antigravity Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Antigravity]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".clinerules": """# Cline / Roo Code Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Cline]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".aider.instruction.md": """# Aider Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Aider]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
""",
    ".github/copilot-instructions.md": """# GitHub Copilot Rules & Handoff Instructions

Before doing any work, you MUST check if `.braingraph/` contains active task details.

## Startup Protocol
1. Read `.braingraph/active_task.md` and `.braingraph/handoff.md` to see the current active task state.
2. Read `.braingraph/resume_context.md` if it exists.
3. Register your process by running:
   `python .braingraph/scripts/braingraph.py register`

## During Work
1. Update `.braingraph/active_task.md` as you complete tasks.
2. Log key updates (1-2 sentences) of your progress to the bottom of `.braingraph/temp_chat_history.md` with:
   `- **[Timestamp] [Copilot]**: Summary of what you just did.`
   This is critical for multi-device sync and crash recovery!

## Handoff Protocol
When you are finishing or if your limits are running low:
- Run `python .braingraph/scripts/braingraph.py handoff` or ask the user to run it to archive the task and prepare a clean handoff.
"""
}

def resolve_safe_project_path(project_path):
    server_root = Path.cwd().resolve()
    if not project_path:
        return server_root
    try:
        # Check against whitelisted discovered projects list
        allowed_projects = discover_projects()
        resolved = str(Path(project_path).resolve()).replace('\\', '/')
        for p in allowed_projects:
            if p["path"] == resolved:
                return Path(p["path"])
    except Exception:
        pass
    return server_root

def get_parent_process_cmd():
    ppid = os.getppid()
    if os.name == 'nt':
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
        '.git', 'node_modules', '.braingraph', 'venv', '.env', 'dist', 'build', 
        '.next', '.venv', '.nuxt', 'target', 'bin', 'obj', '__pycache__', '.agents'
    }
    ignore_files = {
        'CLAUDE.md', '.cursorrules', '.windsurfrules', '.clinerules', 
        '.aider.instruction.md', '.aider.conf.yml'
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
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

def scan_git_status(root_dir=None):
    staged = []
    unstaged = []
    untracked = []
    cwd_path = str(root_dir) if root_dir else None
    try:
        res = subprocess.check_output(["git", "status", "--porcelain"], cwd=cwd_path, text=True, stderr=subprocess.DEVNULL)
        for line in res.split('\n'):
            if not line.strip():
                continue
            status_code = line[:2]
            filename = line[2:].strip()
            
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
                
            if ".braingraph" in filename:
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

def get_git_diff(root_dir=None):
    cwd_path = str(root_dir) if root_dir else None
    try:
        diff = subprocess.check_output(["git", "diff", "--", ":!.braingraph"], cwd=cwd_path, text=True, stderr=subprocess.DEVNULL)
        return diff
    except Exception:
        return ""

def get_last_commit_wip(root_dir=None):
    cwd_path = str(root_dir) if root_dir else None
    try:
        msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], cwd=cwd_path, text=True, stderr=subprocess.DEVNULL).strip()
        if "wip" in msg.lower():
            diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD", "--", ":!.braingraph"], cwd=cwd_path, text=True, stderr=subprocess.DEVNULL)
            return msg, diff
    except Exception:
        pass
    return None, ""

def harvest_antigravity_transcript(max_age_hours=4):
    user_home = Path.home().resolve()
    antigravity_brain_path = user_home / ".gemini" / "antigravity" / "brain"
    if not antigravity_brain_path.exists():
        return None
    
    antigravity_brain_path = str(antigravity_brain_path)
    
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
                    clean_content = re.sub(r'<[^>]+>', '', content)
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
    path = os.path.join(root_dir, ".braingraph", "temp_chat_history.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return None

def load_agents_db(root_dir=None):
    root = Path(root_dir) if root_dir else Path.cwd()
    db_file = root / ".braingraph" / "agents.json"
    if db_file.exists():
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "agents": {
            "Claude Code": {"status": "Available", "limit_type": "Message-based", "max_limit": 50, "reset_time_hours": 5, "last_used": None, "manual_offset": 0},
            "Windsurf Cascade": {"status": "Available", "limit_type": "Premium quota", "max_limit": 500, "reset_time_hours": None, "last_used": None, "manual_offset": 0},
            "Antigravity": {"status": "Available", "limit_type": "Token-based", "max_limit": 100, "reset_time_hours": None, "last_used": None, "manual_offset": 0},
            "Cursor Copilot/Composer": {"status": "Available", "limit_type": "Premium fast", "max_limit": 500, "reset_time_hours": None, "last_used": None, "manual_offset": 0},
            "Aider": {"status": "Available", "limit_type": "Key-based", "max_limit": None, "reset_time_hours": None, "last_used": None, "manual_offset": 0}
        }
    }

def save_agents_db(db, root_dir=None):
    root = Path(root_dir) if root_dir else Path.cwd()
    sb_dir = root / ".braingraph"
    sb_dir.mkdir(exist_ok=True)
    db_file = sb_dir / "agents.json"
    try:
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception:
        pass

def calculate_agent_usage(root_dir):
    usage = {}
    path = os.path.join(root_dir, ".braingraph", "temp_chat_history.md")
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
        print("BRAINGRAPH: AGENT USAGE & AVAILABILITY STATUS")
        print("=" * 65)
        
        agents_list = sorted(list(db["agents"].keys()))
        for idx, name in enumerate(agents_list, 1):
            info = db["agents"][name]
            status = info.get("status", "Available")
            
            color_start = ""
            color_end = ""
            if sys.stdout.isatty():
                if status == "Available":
                    color_start = "\033[92m"
                elif status == "Exhausted":
                    color_start = "\033[91m"
                elif status == "Active":
                    color_start = "\033[96m"
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
    sb_dir = root / ".braingraph"
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

# Graphify integration code
import ast

def get_call_name(node_func):
    if isinstance(node_func, ast.Name):
        return node_func.id
    elif isinstance(node_func, ast.Attribute):
        val = get_call_name(node_func.value)
        if val:
            return f"{val}.{node_func.attr}"
    return None

def resolve_module_path(root_path, importing_file_rel_path, module_name, level):
    # importing_file_rel_path is e.g. "a/b/c.py"
    # level is int (0, 1, 2, ...)
    # module_name is e.g. "auth.utils" or ""
    
    parts = Path(importing_file_rel_path).parent.parts
    
    if level > 0:
        # relative import: go up (level - 1) directories from the parent of importing_file_rel_path
        # level=1 means current directory, level=2 means parent directory, etc.
        go_up = level - 1
        if go_up <= len(parts):
            base_parts = parts[:len(parts) - go_up]
        else:
            base_parts = ()
    else:
        # absolute import: search relative to project root
        base_parts = ()
        
    # Append the module name path
    if module_name:
        mod_path_str = module_name.replace('.', '/')
        full_rel_path = Path(*base_parts) / mod_path_str
    else:
        full_rel_path = Path(*base_parts)
        
    # Check options
    options = [
        f"{full_rel_path}.py",
        f"{full_rel_path}/__init__.py"
    ]
    for opt in options:
        opt_norm = opt.replace('\\', '/').lstrip('/')
        if (root_path / opt_norm).exists():
            return opt_norm
            
    return None

class PythonDependencyVisitor(ast.NodeVisitor):
    def __init__(self, filepath, rel_path):
        self.filepath = filepath
        self.rel_path = rel_path
        self.current_class = None
        self.current_function = None
        self.local_scope = {}
        self.definitions = {}
        self.calls = {}
        
    def get_current_symbol_id(self):
        parts = [self.rel_path]
        if self.current_class:
            parts.append(self.current_class)
        if self.current_function:
            parts.append(self.current_function)
        return "::".join(parts)
        
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.local_scope[asname] = ("module", 0, name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        module = node.module or ""
        level = node.level or 0
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.local_scope[asname] = ("from_module", level, module, name)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        
        class_symbol = self.get_current_symbol_id()
        self.definitions[class_symbol] = {
            "type": "class",
            "label": node.name,
            "file": self.rel_path
        }
        
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        
        func_symbol = self.get_current_symbol_id()
        self.definitions[func_symbol] = {
            "type": "function",
            "label": node.name,
            "file": self.rel_path
        }
        
        self.generic_visit(node)
        self.current_function = old_func
        
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)
        
    def visit_Call(self, node):
        caller_sym = self.get_current_symbol_id()
        self.calls.setdefault(caller_sym, [])
        
        callee_name = get_call_name(node.func)
        if callee_name:
            self.calls[caller_sym].append(callee_name)
            
        self.generic_visit(node)

def parse_python_project(root_dir):
    root_path = Path(root_dir)
    visitors = []
    
    ignore_dirs = {
        '.git', 'node_modules', '.braingraph', 'venv', '.env', 'dist', 'build', 
        '.next', '.venv', '.nuxt', 'target', 'bin', 'obj', '__pycache__', '.agents'
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
        
        for f in filenames:
            if f.endswith('.py') and f != "braingraph.py":
                filepath = os.path.join(dirpath, f)
                rel_path = os.path.relpath(filepath, root_dir).replace('\\', '/')
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file_obj:
                        code = file_obj.read()
                    tree = ast.parse(code, filename=filepath)
                    visitor = PythonDependencyVisitor(filepath, rel_path)
                    visitor.visit(tree)
                    visitors.append(visitor)
                except Exception:
                    pass
                    
    all_definitions = {}
    for visitor in visitors:
        all_definitions.update(visitor.definitions)
        
    for visitor in visitors:
        all_definitions[visitor.rel_path] = {
            "type": "file",
            "label": os.path.basename(visitor.rel_path),
            "file": visitor.rel_path
        }
        
    resolved_edges = []
    
    for visitor in visitors:
        for caller, callees in visitor.calls.items():
            for callee in callees:
                target_sym = None
                parts = callee.split('.')
                
                # Case 1: Call on self, e.g. self.method()
                if parts[0] == "self" and len(parts) > 1 and visitor.current_class:
                    local_target = f"{visitor.rel_path}::{visitor.current_class}::{parts[1]}"
                    if local_target in all_definitions:
                        target_sym = local_target
                
                # Case 2: Check if any prefix of the call chain is in local_scope
                if not target_sym:
                    # Find longest prefix match
                    match_len = 0
                    match_info = None
                    for i in range(1, len(parts) + 1):
                        prefix = ".".join(parts[:i])
                        if prefix in visitor.local_scope:
                            match_len = i
                            match_info = visitor.local_scope[prefix]
                            
                    if match_info:
                        suffix = parts[match_len:]
                        if match_info[0] == "from_module":
                            _, level, mod_name, sym_name = match_info
                            
                            # We imported sym_name from mod_name
                            # It could be a submodule or a symbol inside mod_name
                            is_submodule = False
                            extended_mod_name = f"{mod_name}.{sym_name}" if mod_name else sym_name
                            sub_mod_file = resolve_module_path(root_path, visitor.rel_path, extended_mod_name, level)
                            
                            if sub_mod_file:
                                base_sym = sub_mod_file
                                is_submodule = True
                            else:
                                mod_file = resolve_module_path(root_path, visitor.rel_path, mod_name, level)
                                base_sym = f"{mod_file}::{sym_name}" if mod_file else None
                                
                            if base_sym:
                                # Try full suffix if any
                                if suffix:
                                    full_sym = f"{base_sym}::" + "::".join(suffix)
                                    if full_sym in all_definitions:
                                        target_sym = full_sym
                                    else:
                                        if base_sym in all_definitions:
                                            target_sym = base_sym
                                        else:
                                            # Fallback to the module file itself if base_sym has file extension
                                            if "::" in base_sym:
                                                target_sym = base_sym.split("::")[0]
                                            else:
                                                target_sym = base_sym
                                else:
                                    if base_sym in all_definitions:
                                        target_sym = base_sym
                                    else:
                                        if "::" in base_sym:
                                            target_sym = base_sym.split("::")[0]
                                        else:
                                            target_sym = base_sym
                                        
                        elif match_info[0] == "module":
                            _, level, mod_name = match_info
                            
                            # Try to consume suffix parts as submodules
                            current_mod_name = mod_name
                            current_suffix = list(suffix)
                            resolved_mod_file = None
                            
                            # First, try to resolve the full module name
                            mod_file = resolve_module_path(root_path, visitor.rel_path, current_mod_name, level)
                            if mod_file:
                                resolved_mod_file = mod_file
                                
                            # Try to extend module name with suffix parts to resolve nested submodules
                            consumed = 0
                            for j in range(len(suffix)):
                                next_part = suffix[j]
                                extended_mod_name = f"{current_mod_name}.{next_part}"
                                next_mod_file = resolve_module_path(root_path, visitor.rel_path, extended_mod_name, level)
                                if next_mod_file:
                                    resolved_mod_file = next_mod_file
                                    consumed = j + 1
                                else:
                                    break
                                    
                            if resolved_mod_file:
                                remaining_suffix = suffix[consumed:]
                                if remaining_suffix:
                                    full_sym = f"{resolved_mod_file}::" + "::".join(remaining_suffix)
                                    found = False
                                    for k in range(len(remaining_suffix), 0, -1):
                                        sub_sym = f"{resolved_mod_file}::" + "::".join(remaining_suffix[:k])
                                        if sub_sym in all_definitions:
                                            target_sym = sub_sym
                                            found = True
                                            break
                                    if not found:
                                        target_sym = resolved_mod_file
                                else:
                                    target_sym = resolved_mod_file
                                    
                # Case 3: Check if parts[0] is defined locally in the same file
                if not target_sym:
                    local_target = f"{visitor.rel_path}::{parts[0]}"
                    if local_target in all_definitions:
                        if len(parts) > 1:
                            full_sym = f"{local_target}::" + "::".join(parts[1:])
                            if full_sym in all_definitions:
                                target_sym = full_sym
                            else:
                                target_sym = local_target
                        else:
                            target_sym = local_target
                            
                # If resolved, add edge
                if target_sym and target_sym in all_definitions:
                    resolved_edges.append({
                        "source": caller,
                        "target": target_sym,
                        "relation": "calls"
                    })
                    
    return all_definitions, resolved_edges

def parse_non_python_project(root_dir):
    js_extensions = ('.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.cpp', '.h', '.hpp', '.cc', '.cxx', '.java')
    all_definitions = {}
    edges = []
    
    ignore_dirs = {
        '.git', 'node_modules', '.braingraph', 'venv', '.env', 'dist', 'build', 
        '.next', '.venv', '.nuxt', 'target', 'bin', 'obj', '__pycache__', '.agents'
    }
    
    # Patterns per extension
    patterns = {
        # JS/TS
        '.js': {
            'funcs': [re.compile(r'(?:function\s+([a-zA-Z0-9_$]+)|(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>)')],
            'classes': [re.compile(r'class\s+([a-zA-Z0-9_$]+)')],
            'imports': [re.compile(r'(?:import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|require\(\s*[\'"]([^\'"]+)[\'"]\s*\))')]
        },
        # Go
        '.go': {
            'funcs': [re.compile(r'func\s+([a-zA-Z0-9_]+)\s*\('), re.compile(r'func\s*\([^)]*\)\s*([a-zA-Z0-9_]+)\s*\(')],
            'classes': [re.compile(r'type\s+([a-zA-Z0-9_]+)\s+struct')],
            'imports': [re.compile(r'import\s+"([^"]+)"'), re.compile(r'import\s+\(\s*([\s\S]*?)\s*\)')]
        },
        # Rust
        '.rs': {
            'funcs': [re.compile(r'fn\s+([a-zA-Z0-9_]+)\s*(?:<[^>]*>)?\s*\(')],
            'classes': [re.compile(r'(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)')],
            'imports': [re.compile(r'use\s+([^;]+);')]
        },
        # C/C++
        '.cpp': {
            'funcs': [re.compile(r'[a-zA-Z0-9_:<>]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:const)?\s*\{')],
            'classes': [re.compile(r'(?:class|struct)\s+([a-zA-Z0-9_]+)')],
            'imports': [re.compile(r'#include\s+["<]([^">]+)[">]')]
        },
        # Java
        '.java': {
            'funcs': [re.compile(r'(?:public|protected|private|static|\s)+[a-zA-Z0-9_<>@]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[a-zA-Z0-9_,\s]+)?\s*\{')],
            'classes': [re.compile(r'(?:class|interface|enum)\s+([a-zA-Z0-9_]+)')],
            'imports': [re.compile(r'import\s+([^;]+);')]
        }
    }
    
    # Map other extensions to the base ones
    ext_map = {
        '.ts': '.js', '.jsx': '.js', '.tsx': '.js',
        '.h': '.cpp', '.hpp': '.cpp', '.cc': '.cpp', '.cxx': '.cpp'
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
        
        for f in filenames:
            _, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext in js_extensions:
                base_ext = ext_map.get(ext, ext)
                lang_pat = patterns.get(base_ext)
                if not lang_pat:
                    continue
                    
                filepath = os.path.join(dirpath, f)
                rel_path = os.path.relpath(filepath, root_dir).replace('\\', '/')
                
                file_sym = rel_path
                all_definitions[file_sym] = {
                    "type": "file",
                    "label": f,
                    "file": rel_path
                }
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file_obj:
                        file_content = file_obj.read()
                    
                    local_definitions = []
                    
                    # 1. Match functions
                    for pat in lang_pat['funcs']:
                        for match in pat.finditer(file_content):
                            name = None
                            for g in match.groups():
                                if g:
                                    name = g.strip()
                                    break
                            if name:
                                sym = f"{rel_path}::{name}"
                                all_definitions[sym] = {
                                    "type": "function",
                                    "label": name,
                                    "file": rel_path
                                }
                                local_definitions.append(sym)
                                
                    # 2. Match classes / structs / types
                    for pat in lang_pat['classes']:
                        for match in pat.finditer(file_content):
                            name = match.group(1).strip() if match.group(1) else None
                            if name:
                                sym = f"{rel_path}::{name}"
                                all_definitions[sym] = {
                                    "type": "class",
                                    "label": name,
                                    "file": rel_path
                                }
                                local_definitions.append(sym)
                                
                    # 3. Match imports / includes / uses
                    imported_files = []
                    for pat in lang_pat['imports']:
                        for match in pat.finditer(file_content):
                            imp_raw = match.group(1)
                            if not imp_raw:
                                continue
                            
                            # Parse multiple imports if it's block format (Go import block)
                            imports_list = []
                            if base_ext == '.go' and '(' in match.group(0):
                                for line in imp_raw.split('\n'):
                                    line_clean = line.strip().strip('"')
                                    if line_clean and not line_clean.startswith('//'):
                                        imports_list.append(line_clean)
                            else:
                                imports_list.append(imp_raw.strip().strip('"').strip("'"))
                                
                            for imp_path in imports_list:
                                if base_ext == '.js':
                                    curr_dir = os.path.dirname(rel_path)
                                    resolved_rel = os.path.normpath(os.path.join(curr_dir, imp_path)).replace('\\', '/')
                                    possible_files = [
                                        resolved_rel,
                                        f"{resolved_rel}.ts",
                                        f"{resolved_rel}.tsx",
                                        f"{resolved_rel}.js",
                                        f"{resolved_rel}.jsx",
                                        f"{resolved_rel}/index.ts",
                                        f"{resolved_rel}/index.js",
                                    ]
                                    for p_file in possible_files:
                                        if os.path.exists(os.path.join(root_dir, p_file)):
                                            imported_files.append(p_file)
                                            break
                                            
                                elif base_ext == '.cpp':
                                    curr_dir = os.path.dirname(rel_path)
                                    p_file = os.path.normpath(os.path.join(curr_dir, imp_path)).replace('\\', '/')
                                    if os.path.exists(os.path.join(root_dir, p_file)):
                                        imported_files.append(p_file)
                                    else:
                                        base_header = os.path.basename(imp_path)
                                        for root, dirs, files in os.walk(root_dir):
                                            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
                                            if base_header in files:
                                                found_p = os.path.relpath(os.path.join(root, base_header), root_dir).replace('\\', '/')
                                                imported_files.append(found_p)
                                                break
                                                
                                elif base_ext == '.go':
                                    parts_go = imp_path.split('/')
                                    for idx in range(len(parts_go)):
                                        candidate = '/'.join(parts_go[idx:])
                                        cand_dir = os.path.join(root_dir, candidate)
                                        if os.path.isdir(cand_dir):
                                            for f_go in os.listdir(cand_dir):
                                                if f_go.endswith('.go'):
                                                    imported_files.append(f"{candidate}/{f_go}".replace('\\', '/'))
                                            break
                                            
                                elif base_ext == '.rs':
                                    rs_path = imp_path.replace('::', '/')
                                    prefixes = ['crate/', 'super/', 'self/']
                                    for pref in prefixes:
                                        if rs_path.startswith(pref):
                                            rs_path = rs_path[len(pref):]
                                    possible_files = [
                                        f"{rs_path}.rs",
                                        f"{rs_path}/mod.rs",
                                        f"src/{rs_path}.rs",
                                        f"src/{rs_path}/mod.rs",
                                    ]
                                    for p_file in possible_files:
                                        if os.path.exists(os.path.join(root_dir, p_file)):
                                            imported_files.append(p_file)
                                            break
                                            
                                elif base_ext == '.java':
                                    java_path = imp_path.replace('.', '/')
                                    possible_files = [
                                        f"{java_path}.java",
                                        f"src/main/java/{java_path}.java",
                                        f"src/{java_path}.java",
                                    ]
                                    for p_file in possible_files:
                                        if os.path.exists(os.path.join(root_dir, p_file)):
                                            imported_files.append(p_file)
                                            break
                                            
                    for imp_file in list(set(imported_files)):
                        edges.append({
                            "source": file_sym,
                            "target": imp_file,
                            "relation": "imports"
                        })
                        for loc_sym in local_definitions:
                            edges.append({
                                "source": loc_sym,
                                "target": imp_file,
                                "relation": "depends_on"
                            })
                except Exception:
                    pass
                    
    return all_definitions, edges

def load_code_graph(root_dir):
    print("[BrainGraph] Indexing codebase and generating dependency map...")
    t0 = datetime.datetime.now()
    
    py_defs, py_edges = parse_python_project(root_dir)
    non_py_defs, non_py_edges = parse_non_python_project(root_dir)
    
    nodes = {}
    nodes.update(py_defs)
    nodes.update(non_py_defs)
    
    edges = []
    edges.extend(py_edges)
    edges.extend(non_py_edges)
    
    file_to_nodes = {}
    parents = {}
    
    for nid, val in nodes.items():
        filepath = val.get("file")
        if filepath:
            file_to_nodes.setdefault(filepath, []).append(nid)
            
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        relation = edge.get("relation") or ""
        
        if src and tgt:
            parents.setdefault(tgt, []).append((src, relation))
            
    t1 = datetime.datetime.now()
    elapsed = (t1 - t0).total_seconds()
    print(f"[BrainGraph] Successfully built local AST code graph in {elapsed:.3f} seconds ({len(nodes)} nodes, {len(edges)} edges).")
    
    return {
        "nodes": nodes,
        "file_to_nodes": file_to_nodes,
        "parents": parents
    }

def analyze_downstream_impact(graph, modified_files, max_depth=2, root_dir=None):
    if not graph:
        return None, ""
        
    nodes = graph["nodes"]
    file_to_nodes = graph["file_to_nodes"]
    parents = graph["parents"]
    
    affected_symbols = set()
    relations = []
    
    for mf in modified_files:
        mf_norm = mf.replace('\\', '/')
        nids = file_to_nodes.get(mf_norm, [])
        
        visited = set(nids)
        queue = [(nid, 0) for nid in nids]
        
        while queue:
            curr, depth = queue.pop(0)
            if depth >= max_depth:
                continue
                
            for parent, relation in parents.get(curr, []):
                if parent not in visited:
                    visited.add(parent)
                    queue.append((parent, depth + 1))
                    
                    p_info = nodes.get(parent, {})
                    p_label = p_info.get("label") or parent
                    p_file = p_info.get("file") or p_info.get("path") or ""
                    if p_file:
                        ref_dir = root_dir if root_dir else Path.cwd()
                        p_file = os.path.relpath(p_file, ref_dir).replace('\\', '/')
                    
                    affected_symbols.add((p_label, p_file))
                    
                    curr_info = nodes.get(curr, {})
                    curr_label = curr_info.get("label") or curr
                    relations.append((curr_label, p_label, relation))
                    
    mermaid = ""
    if relations:
        mermaid = "```mermaid\ngraph TD\n"
        def clean(label):
            return label.replace(':', '_').replace('.', '_').replace('-', '_').replace(' ', '_').replace('>', '_').replace('<', '_')
            
        for child, parent, rel in relations:
            child_clean = clean(child)
            parent_clean = clean(parent)
            rel_label = f"|{rel}|" if rel else ""
            mermaid += f'    {child_clean}["{child}"] -->{rel_label} {parent_clean}["{parent}"]\n'
        mermaid += "```"
        
    return sorted(list(affected_symbols)), mermaid

def cmd_watchdog():
    import time
    root = Path.cwd()
    sb_dir = root / ".braingraph"
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
    script_path = root / ".braingraph" / "scripts" / "braingraph.py"
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
    lock_file = root / ".braingraph" / "watchdog.lock"
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
            
    pid_file = root / ".braingraph" / "agent.pid"
    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass

def cmd_init(root_dir=None):
    root = Path(root_dir) if root_dir else Path.cwd()
    print("==================================================")
    print(f"Initializing BrainGraph Configuration Rules in {root}...")
    print("==================================================")
    
    sb_dir = root / ".braingraph"
    sb_dir.mkdir(exist_ok=True)
    (sb_dir / "history").mkdir(exist_ok=True)
    (sb_dir / "scripts").mkdir(exist_ok=True)
    
    for name, content in RULES_TEMPLATES.items():
        filepath = root / name
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if filepath.exists():
            print(f"  Configuration file {name} already exists. Skipping.")
        else:
            filepath.write_text(content, encoding="utf-8")
            print(f"  Created {name}")
            
    at_file = sb_dir / "active_task.md"
    if not at_file.exists():
        at_file.write_text("""# Active Task: [No active task loaded]

Run `python .braingraph/scripts/braingraph.py start "Task Name"` to begin.

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
        print("  Created .braingraph/active_task.md")
        
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
        print("  Created .braingraph/handoff.md")
        
    tc_file = sb_dir / "temp_chat_history.md"
    if not tc_file.exists():
        tc_file.write_text("# Sync Chat History\n\n", encoding="utf-8")
        print("  Created .braingraph/temp_chat_history.md")
        
    # Copy the script to .braingraph/scripts/braingraph.py if it is running from elsewhere
    import shutil
    try:
        src_script = Path(__file__)
        shutil.copy2(src_script, sb_dir / "scripts" / "braingraph.py")
        print("  Copied braingraph.py script to target project.")
        
        src_html = src_script.parent / "dashboard.html"
        if src_html.exists():
            shutil.copy2(src_html, sb_dir / "scripts" / "dashboard.html")
            print("  Copied dashboard.html to target project.")
    except Exception as e:
        print(f"  Warning: Could not copy files: {e}")
        
    print("\nBrainGraph successfully initialized!")

def cmd_start(task_name):
    root = Path.cwd()
    sb_dir = root / ".braingraph"
    if not sb_dir.exists():
        print("Error: .braingraph not initialized. Run init first.")
        sys.exit(1)
        
    print(f"Starting task: {task_name}")
    
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
    
    tc_file = sb_dir / "temp_chat_history.md"
    tc_file.write_text(f"# Sync Chat History - {task_name}\n\n", encoding="utf-8")
    
    rc_file = sb_dir / "resume_context.md"
    if rc_file.exists():
        rc_file.unlink()
        
    print("Task initialized successfully. Ready for coding agents!")
    start_watchdog_background()

def cmd_resume():
    root = Path.cwd()
    sb_dir = root / ".braingraph"
    if not sb_dir.exists():
        print("Error: .braingraph not initialized. Run init first.")
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
    
    at_content = ""
    at_file = sb_dir / "active_task.md"
    if at_file.exists():
        at_content = at_file.read_text(encoding="utf-8")
        
    ho_content = ""
    ho_file = sb_dir / "handoff.md"
    if ho_file.exists():
        ho_content = ho_file.read_text(encoding="utf-8")
        
    staged, unstaged, untracked = scan_git_status()
    git_diff = get_git_diff()
    recent_files = scan_recent_files(root)
    wip_msg, wip_diff = get_last_commit_wip()
    
    chat_history = harvest_temp_chat_history(root)
    antigravity_chat = harvest_antigravity_transcript()
    aider_chat = harvest_aider_history(root)
    
    # Load and process code graphify output
    graph = load_code_graph(root)
    modified_files = list(set([x[1] for x in staged + unstaged] + untracked))
    for rf, t in recent_files:
        modified_files.append(rf)
    modified_files = list(set(modified_files))
    
    affected_symbols, mermaid_diagram = analyze_downstream_impact(graph, modified_files)
    
    # Save Mermaid diagram to active_graph.md
    if mermaid_diagram:
        graph_md = f"# Active Changes Callflow Map\n\nThis diagram maps your in-progress modifications and their downstream dependencies:\n\n{mermaid_diagram}\n"
        with open(sb_dir / "active_graph.md", "w", encoding="utf-8") as f:
            f.write(graph_md)
    else:
        if (sb_dir / "active_graph.md").exists():
            (sb_dir / "active_graph.md").unlink()
            
    lines = []
    lines.append(f"# BRAINGRAPH RESUME CONTEXT SUMMARY")
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
                
        filesystem_only = [rf for rf, t in recent_files if rf not in [x[1] for x in staged + unstaged] and rf not in untracked]
        if filesystem_only:
            lines.append("### Recently Autosaved/Modified Files (Last 4h, not staged/tracked):")
            for rf in filesystem_only:
                lines.append(f"- `[filesystem]` {rf}")
                
    # Downstream Dependency Impact Analysis
    if affected_symbols:
        lines.append("\n### Downstream Impact Radius (Graphify AST callers):")
        lines.append("The following symbols depend on the code you modified. Be careful when updating them:")
        for sym, f in affected_symbols:
            lines.append(f"- `{sym}` (in `{f}`)")
        if mermaid_diagram:
            lines.append("\n*Note: Visual call-flow map generated in `.braingraph/active_graph.md`*")
            
    if git_diff.strip():
        lines.append("\n### Uncommitted Git Diff:")
        lines.append("```diff")
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
    lines.append(f"2. Inspect the files listed in **Workspace Changes** and check **Downstream Impact Radius**.")
    lines.append(f"3. Run any tests or build steps to ensure nothing is currently broken.")
    lines.append(f"4. Proceed to finish the remaining subtasks in `active_task.md`.")
    lines.append(f"5. Maintain `.braingraph/temp_chat_history.md` by logging your work.")
    
    context_md = "\n".join(lines)
    
    rc_file = sb_dir / "resume_context.md"
    rc_file.write_text(context_md, encoding="utf-8")
    
    print(context_md)
    print(f"\n==================================================")
    print(f"Context compiled and saved to `.braingraph/resume_context.md`.")
    print(f"Incoming agent: please read `.braingraph/resume_context.md` to begin.")
    print(f"==================================================")

def cmd_handoff():
    root = Path.cwd()
    sb_dir = root / ".braingraph"
    if not sb_dir.exists():
        print("Error: .braingraph not initialized. Run init first.")
        sys.exit(1)
        
    print("Generating Handoff...")
    
    print("\nSummary of accomplishments (what did you finish?):")
    accomplishments = ""
    if sys.stdin.isatty():
        try:
            accomplishments = input("> ")
        except (KeyboardInterrupt, EOFError):
            pass
    if not accomplishments:
        accomplishments = "Agent session ended. Progress saved in git and active_task.md."
        
    at_file = sb_dir / "active_task.md"
    at_content = ""
    if at_file.exists():
        at_content = at_file.read_text(encoding="utf-8")
        
    staged, unstaged, untracked = scan_git_status()
    recent_files = scan_recent_files(root)
    files_edited = set([x[1] for x in staged + unstaged] + untracked)
    for rf, t in recent_files:
        files_edited.add(rf)
        
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
    ho_file = sb_dir / "handoff.md"
    if ho_file.exists():
        old_ho = ho_file.read_text(encoding="utf-8")
        if "No active handoff" not in old_ho:
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_ho_file = history_dir / f"handoff_{hist_ts}.md"
            hist_ho_file.write_text(old_ho, encoding="utf-8")
            
    ho_file.write_text(ho_content, encoding="utf-8")
    print(f"Handoff generated at `.braingraph/handoff.md`")
    
    if at_file.exists():
        old_at = at_file.read_text(encoding="utf-8")
        if "No active task loaded" not in old_at:
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_at_file = history_dir / f"task_{hist_ts}.md"
            hist_at_file.write_text(old_at, encoding="utf-8")
            
    tc_file = sb_dir / "temp_chat_history.md"
    if tc_file.exists():
        tc_content = tc_file.read_text(encoding="utf-8")
        if tc_content.strip():
            history_dir = sb_dir / "history"
            hist_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            hist_tc_file = history_dir / f"chat_{hist_ts}.md"
            hist_tc_file.write_text(tc_content, encoding="utf-8")
        tc_file.write_text("# Sync Chat History\n\n", encoding="utf-8")
        
    rc_file = sb_dir / "resume_context.md"
    if rc_file.exists():
        rc_file.unlink()
        
    stop_watchdog()

def markdown_to_html(md_text):
    if not md_text:
        return ""
    html_lines = []
    in_list = False
    for line in md_text.splitlines():
        line_strip = line.strip()
        if not line_strip:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
            
        if line_strip.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{line_strip[2:]}</h1>")
        elif line_strip.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{line_strip[3:]}</h2>")
        elif line_strip.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{line_strip[4:]}</h3>")
        elif line_strip.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = line_strip[2:]
            if content.startswith("[ ]") or content.startswith("[x]") or content.startswith("[/]"):
                status = content[1]
                text = content[4:].strip()
                checked = "checked" if status == "x" else ""
                if status == "/":
                    html_lines.append(f"<li><input type='checkbox' disabled style='margin-right: 0.5rem;'><span style='color: var(--accent-amber); font-weight: 500;'>[/] {text}</span></li>")
                else:
                    html_lines.append(f"<li><input type='checkbox' {checked} disabled style='margin-right: 0.5rem;'>{text}</li>")
            else:
                html_lines.append(f"<li>{content}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{line_strip}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)

import http.server
import socketserver

def discover_projects(root_dir=None):
    root = Path(root_dir) if root_dir else Path.cwd()
    projects = []
    seen_paths = set()
    
    # Check the root directory itself
    try:
        has_git = (root / ".git").is_dir()
        has_bg = (root / ".braingraph").is_dir()
        if has_git or has_bg:
            resolved_path = str(root.resolve()).replace('\\', '/')
            projects.append({
                "name": root.name or str(root),
                "path": resolved_path,
                "has_git": has_git,
                "has_braingraph": has_bg
            })
            seen_paths.add(resolved_path)
    except Exception:
        pass
        
    # Check immediate subdirectories
    try:
        for item in root.iterdir():
            if item.is_dir():
                if item.name.startswith('.') and item.name not in ('.git', '.braingraph'):
                    continue
                try:
                    item_git = (item / ".git").is_dir()
                    item_bg = (item / ".braingraph").is_dir()
                    if item_git or item_bg:
                        resolved_path = str(item.resolve()).replace('\\', '/')
                        if resolved_path not in seen_paths:
                            projects.append({
                                "name": item.name,
                                "path": resolved_path,
                                "has_git": item_git,
                                "has_braingraph": item_bg
                            })
                            seen_paths.add(resolved_path)
                except Exception:
                    pass
    except Exception:
        pass
        
    projects.sort(key=lambda x: x["name"].lower())
    return projects

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress request logging to keep the console output clean
        pass
        
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = Path(__file__).parent / "dashboard.html"
            if html_path.exists():
                self.wfile.write(html_path.read_bytes())
            else:
                self.wfile.write(b"<h1>Dashboard file not found</h1>")
        elif path == "/api/projects":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            projects = discover_projects()
            self.wfile.write(json.dumps({"projects": projects}).encode("utf-8"))
        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            proj_param = query_params.get("project", [None])[0]
            root = resolve_safe_project_path(proj_param)
                
            sb_dir = root / ".braingraph"
            has_bg = sb_dir.is_dir()
            
            at_content = ""
            if has_bg:
                at_file = sb_dir / "active_task.md"
                if at_file.exists():
                    at_content = at_file.read_text(encoding="utf-8")
            else:
                at_content = "# Project Not Initialized\n\nBrainGraph is not yet initialized for this project directory."
                
            at_html = markdown_to_html(at_content)
            
            staged, unstaged, untracked = scan_git_status(root)
            recent_files = scan_recent_files(root)
            
            graph = load_code_graph(root)
            modified_files = list(set([x[1] for x in staged + unstaged] + untracked))
            for rf, t in recent_files:
                modified_files.append(rf)
            modified_files = list(set(modified_files))
            
            affected_symbols, mermaid_diagram = analyze_downstream_impact(graph, modified_files, root_dir=root)
            
            db = load_agents_db(root)
            usage = calculate_agent_usage(root)
            
            status_data = {
                "has_braingraph": has_bg,
                "project_path": str(root).replace('\\', '/'),
                "active_task_html": at_html,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "agents": db.get("agents", {}),
                "usage": usage,
                "mermaid_diagram": mermaid_diagram
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        content_length = int(self.headers.get('Content-Length', 0))
        data = {}
        if content_length > 0:
            try:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
            except Exception:
                pass
                
        project_path = data.get("project")
        if not project_path:
            project_path = query_params.get("project", [None])[0]
            
        root = resolve_safe_project_path(project_path)
            
        if path == "/api/toggle_agent":
            name = data.get("name")
            new_status = data.get("status")
            
            db = load_agents_db(root)
            if name in db.get("agents", {}):
                db["agents"][name]["status"] = new_status
                db["agents"][name]["last_updated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_agents_db(db, root)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"success":true}')
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Agent not found"}')
        elif path == "/api/reset_offsets":
            db = load_agents_db(root)
            for name in db.get("agents", {}):
                db["agents"][name]["manual_offset"] = 0
            save_agents_db(db, root)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif path == "/api/init_project":
            if root.exists() and root.is_dir():
                cmd_init(root)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"success":true}')
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Project path does not exist or is not a directory"}')
        else:
            self.send_response(404)
            self.end_headers()

def cmd_dashboard():
    import webbrowser
    import time
    import threading
    
    port = 9090
    server_address = ('', port)
    
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        
    try:
        httpd = ThreadingHTTPServer(server_address, DashboardHandler)
        print(f"==================================================")
        print(f"BRAINGRAPH WEB DASHBOARD")
        print(f"==================================================")
        print(f"  Local Control Panel: http://localhost:{port}")
        print(f"  Press Ctrl+C to stop the server.")
        print(f"==================================================")
        
        def open_browser():
            time.sleep(0.5)
            webbrowser.open(f"http://localhost:{port}")
            
        threading.Thread(target=open_browser, daemon=True).start()
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("==================================================")
        print("BRAINGRAPH CLI: Contextual Multi-Agent Handoff")
        print("==================================================")
        print("Usage: python braingraph.py [init | start <task> | resume | handoff | agents | dashboard | register [pid] | watchdog]")
        print("\nCommands:")
        print("  init            Initialize configurations for all supported AI agents")
        print("  start <task>    Initialize a new active task")
        print("  resume          Scan changes & local history to compile context for next agent")
        print("  handoff         Generate a handoff document and archive current state")
        print("  agents          Display interactive usage menu and agent status")
        print("  dashboard       Launch the local Web UI Control Panel dashboard")
        print("  register [pid]  Register the parent shell or agent process PID")
        print("  watchdog        Start the background monitoring watchdog")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "init":
        cmd_init()
    elif cmd == "start":
        if len(sys.argv) < 3:
            print("Error: Please specify a task name. E.g. python braingraph.py start 'Fix authentication bug'")
            sys.exit(1)
        cmd_start(sys.argv[2])
    elif cmd == "resume":
        cmd_resume()
    elif cmd == "handoff":
        cmd_handoff()
    elif cmd == "agents":
        cmd_agents()
    elif cmd == "dashboard":
        cmd_dashboard()
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
