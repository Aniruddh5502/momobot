import re
from rich.console import Console
from typing import Dict, Any
from CMD.registry import CommandRegistry

# Shared console for command output
console = Console()

def register_session_commands(registry: CommandRegistry):
    """Registers all session-related commands to the provided registry."""
    
    @registry.register("/session")
    def handle_sessions(args: str, state: Dict[str, Any], context: Dict[str, Any]):
        sm = context.get("sm")
        if not sm:
            console.print("[bold red]Error: SessionManager not found in context.[/bold red]")
            return {"skip": False}

        # If args is empty or just "/sessions", list sessions
        # The registry handles both /session and /sessions if registered, 
        # but here we treat /session with no args as a list command.
        if not args or args.strip() == "s": # handle /sessions if routed here
            sessions = sm.list_sessions()
            if not sessions:
                console.print("\n[yellow]No saved sessions found.[/yellow]")
                return {"skip": True} 
            
            console.print("\n[bold]Recent Sessions:[/bold]")
            for i, name in enumerate(sessions, 1):
                console.print(f" {i}. [cyan]{name}[/cyan]")
            console.print("[dim]Use /session{i} to resume one of these.\n[/dim]")
            return {"skip": True}

        # Handle /session{id} logic
        # args here would be "1", "2", etc.
        match = re.match(r"(\d+)", args.strip())
        if match:
            idx = int(match.group(1)) - 1
            sessions = sm.list_sessions()
            if 0 <= idx < len(sessions):
                target = sessions[idx]
                resumed = sm.load_session(target)
                if resumed:
                    console.print(f"[bold green]Resuming session: {target}[/bold green]")
                    
                    # To truly replace history in an 'add_messages' state, 
                    # we must remove all current messages first.
                    from langgraph.graph.message import RemoveMessage
                    current_messages = state.get("messages", [])
                    removal_list = [RemoveMessage(id=m.id) for m in current_messages if m.id]
                    resumed_messages = resumed.get("messages", [])
                    
                    return {
                        **resumed, 
                        "messages": removal_list + resumed_messages, 
                        "end": "", 
                        "skip": True
                    }
                else:
                    console.print(f"[bold red]Failed to load session {target}[/bold red]")
            else:
                console.print(f"[bold red]Invalid session index {idx+1}[/bold red]")
        else:
            console.print("[bold red]Usage: /session[index] or /session to list.[/bold red]")
            
        return {"skip": True}

    @registry.register("/sessions")
    def handle_sessions_alias(args: str, state: Dict[str, Any], context: Dict[str, Any]):
        # Alias for /session
        return handle_sessions(args, state, context)

    @registry.register("/clear")
    def handle_clear(args: str, state: Dict[str, Any], context: Dict[str, Any]):
        sm = context.get("sm")
        if not sm:
            console.print("[bold red]Error: SessionManager not found in context.[/bold red]")
            return {"skip": False}

        # 1. Save current state as a session before clearing
        messages = state.get("messages", [])
        if messages:
            from langgraph.graph.message import RemoveMessage
            # Use the first message content as a default session name
            first_content = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
            session_name = first_content[:50].strip() or "cleared_session"
            sm.save_session(session_name, state)
            console.print(f"[dim]Current session archived as: {session_name}[/dim]")
            
            # To truly clear messages in an 'add_messages' annotated state, 
            # we must provide a list of RemoveMessage objects for existing IDs.
            removal_list = [RemoveMessage(id=m.id) for m in messages if m.id]
            console.print("[bold yellow]Session cleared. Starting fresh![/bold yellow]")
            return {
                "messages": removal_list, 
                "summary": "", 
                "token_usages": 0, 
                "skip": True
            }
        
        console.print("[bold yellow]Session cleared. Starting fresh![/bold yellow]")
        return {
            "messages": [], 
            "summary": "", 
            "token_usages": 0, 
            "skip": True
        }
