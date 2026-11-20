"""Wake the existing Streamlit session runner without a visible browser or orders."""
import json, time, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def runtime_recent(root=ROOT, now=None):
    now=now or datetime.now(timezone.utc)
    try:
        p=json.loads((root/'.traderia/mt5_demo_robot_background_state.json').read_text())
        age=(now-datetime.fromisoformat(p['updated_at'])).total_seconds()
        return 0<=age<180
    except (OSError,ValueError,KeyError,TypeError):return False

def main():
    if "--force" not in sys.argv and runtime_recent():return 0
    import websocket
    from streamlit.proto.BackMsg_pb2 import BackMsg
    from application.operational_audit import event
    event('Inicializacao automatica','TENTATIVA','Ciclo sem atualizacao: iniciar sessao interna no painel existente. Agenda e estado operacional preservados.')
    ws=None
    state_path=ROOT/'.traderia/mt5_demo_robot_background_state.json'
    before=state_path.read_bytes() if state_path.exists() else b''
    try:
        ws=websocket.create_connection('ws://127.0.0.1:8532/_stcore/stream',subprotocols=['streamlit'],timeout=5,origin='http://127.0.0.1:8532')
        msg=BackMsg();msg.rerun_script.query_string='';ws.send_binary(msg.SerializeToString())
        end=time.monotonic()+45
        while time.monotonic()<end:
            if runtime_recent() and state_path.read_bytes()!=before:
                event('Inicializacao automatica','CONFIRMADO','Ciclo voltou a atualizar; nao confirma envio de ordem.')
                return 0
            try:ws.recv()
            except websocket.WebSocketTimeoutException:pass
        event('Inicializacao automatica','FALHA','Servidor respondeu, mas ciclo nao atualizou. Nao reiniciar processo de execucao cegamente.')
        return 1
    except Exception as exc:
        event('Inicializacao automatica','FALHA',type(exc).__name__)
        return 1
    finally:
        if ws:ws.close()

if __name__=='__main__':raise SystemExit(main())
