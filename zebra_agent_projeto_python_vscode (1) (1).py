# Projeto: ZebraAgent — Assistente de navegação para clientes cegos (simulação)
# Arquivo único com estrutura de projeto e múltiplos módulos embutidos.
# Salve como README e crie os ficheiros separados conforme indicado abaixo.

"""
Estrutura sugerida do projeto (criar os ficheiros correspondentes em VSCode):

zebra_agent/
├─ README.md                -> este ficheiro explicativo
├─ requirements.txt         -> dependências
├─ src/
│  ├─ main.py               -> ponto de entrada (simulação CLI)
│  ├─ sensors.py            -> classes que simulam RFID / Localização / Carrinho
│  ├─ agent.py              -> AgentAI (planeamento + cálculo de passos/direções)
│  ├─ voice.py              -> interface de voz (opcional: STT/TTS) + fallback textual
│  └─ utils.py              -> utilitários (geometria, logs)
├─ tests/
│  └─ test_navigation.py    -> testes simples

Objetivo: ter um sistema local que simula:
- Mapa da loja com produtos posicionados (x,y,z -> prateleira)
- RFID / beacons que retornam posições aproximadas
- "Zebra" (dispositivo handheld) que o utilizador passa sobre a prateleira e obtém confirmação por apito
- Carrinho com sensor que detecta produto adicionado (simulação por leitura RFID)
- AgentAI que transforma pedido de lista de compras em rota e orientações por passos

Este ficheiro contém o código sugerido para cada módulo — cole e salve com os nomes acima.

------------------------------------------------------------------
# requirements.txt
------------------------------------------------------------------
# Minimal
numpy>=1.24
pydantic>=1.10
# Optional (voz)
speechrecognition>=3.8.1
pyttsx3>=2.90
# For tests
pytest>=7.0

------------------------------------------------------------------
# src/utils.py
------------------------------------------------------------------
from typing import Tuple
import math

def distance(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    return math.hypot(a[0]-b[0], a[1]-b[1])

def meters_to_steps(meters: float, step_length_m: float = 0.75) -> int:
    # estimativa: passo médio 0.75m
    return max(1, int(round(meters / step_length_m)))

def direction_from_vector(dx: float, dy: float) -> str:
    # devolve uma direcao simples baseada no vetor (dx,dy)
    if abs(dx) < 0.3 and abs(dy) < 0.3:
        return 'em frente'
    angle = math.degrees(math.atan2(dy, dx))
    # 0 graus -> direita, 90 -> frente, 180/-180 -> esquerda, -90 -> tras
    if -45 <= angle <= 45:
        return 'direita'
    if 45 < angle <= 135:
        return 'frente'
    if angle > 135 or angle < -135:
        return 'esquerda'
    return 'tras'

------------------------------------------------------------------
# src/sensors.py
------------------------------------------------------------------
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import random
from .utils import distance

@dataclass
class Product:
    uid: str
    name: str
    position: Tuple[float,float]
    shelf_level: int  # 0 = piso/baixo, 1 = meio, 2 = cima

class StoreMap:
    def __init__(self):
        self.products: Dict[str, Product] = {}

    def add_product(self, uid: str, name: str, pos: Tuple[float,float], shelf_level: int):
        self.products[uid] = Product(uid, name, pos, shelf_level)

    def find_by_name(self, name: str) -> Optional[Product]:
        for p in self.products.values():
            if p.name.lower() == name.lower():
                return p
        return None

    def nearest_product_tag(self, estimated_pos: Tuple[float,float], radius: float = 3.0):
        # devolve produtos dentro de raio
        res = []
        for p in self.products.values():
            d = distance(estimated_pos, p.position)
            if d <= radius:
                res.append((p, d))
        res.sort(key=lambda x: x[1])
        return res

class RFIDReader:
    """Leituras RFID simuladas: devolve uid com ruído e alcance.
    """
    def __init__(self, store_map: StoreMap, range_meters: float = 2.0, noise_prob: float = 0.05):
        self.store_map = store_map
        self.range = range_meters
        self.noise_prob = noise_prob

    def scan(self, position: Tuple[float,float]):
        # devolve uma lista de (uid, distance) possíveis
        found = []
        for uid, p in self.store_map.products.items():
            d = distance(position, p.position)
            if d <= self.range and random.random() > self.noise_prob:
                found.append((uid, d))
        return found

class Cart:
    def __init__(self, cart_id: str):
        self.cart_id = cart_id
        self.contents = []

    def add(self, uid: str):
        self.contents.append(uid)

    def has(self, uid: str) -> bool:
        return uid in self.contents

class ZebraDevice:
    def __init__(self, sensitivity: float = 0.5):
        # sensitivity representa quanto próximo deve estar ao tag para apitar
        self.sensitivity = sensitivity

    def sweep(self, product: Product, device_pos: Tuple[float,float], device_height: int) -> bool:
        # Simula passar o zebra: verificamos se x,y está próximo e shelf level coincide
        from .utils import distance
        d = distance(product.position, device_pos)
        if d <= self.sensitivity and product.shelf_level == device_height:
            return True
        return False

------------------------------------------------------------------
# src/agent.py
------------------------------------------------------------------
from typing import List, Tuple
from .sensors import StoreMap, RFIDReader, Cart, Product
from .utils import distance, meters_to_steps, direction_from_vector

class AgentAI:
    def __init__(self, store_map: StoreMap, reader: RFIDReader):
        self.store_map = store_map
        self.reader = reader

    def parse_shopping_list(self, text: str) -> List[str]:
        # parser simples: separa por vírgulas e 'e'
        items = []
        bits = text.replace(' e ', ',').split(',')
        for b in bits:
            s = b.strip()
            if s:
                items.append(s)
        return items

    def plan_route(self, current_pos: Tuple[float,float], items: List[str]) -> List[Tuple[Product, int]]:
        # estratégia simples: buscar produto por nome -> ordenar por distância (grosso modo)
        found = []
        for it in items:
            p = self.store_map.find_by_name(it)
            if p:
                found.append(p)
            else:
                print(f"Aviso: produto '{it}' não encontrado na base de dados")
        # ordenar por distância desde pos atual (não otimizado TSP)
        found.sort(key=lambda p: distance(current_pos, p.position))
        # devolver pares (product, steps_from_previous)
        route = []
        prev = current_pos
        for p in found:
            d = distance(prev, p.position)
            route.append((p, meters_to_steps(d)))
            prev = p.position
        return route

    def give_directions(self, from_pos: Tuple[float,float], to_product: Product) -> Tuple[int,str]:
        dx = to_product.position[0] - from_pos[0]
        dy = to_product.position[1] - from_pos[1]
        steps = meters_to_steps(distance(from_pos, to_product.position))
        dir_text = direction_from_vector(dx, dy)
        return steps, dir_text

------------------------------------------------------------------
# src/voice.py
------------------------------------------------------------------
# Interface simples: tenta STT para transformar fala em texto e TTS para falar instrucoes.
# Implementa fallback textual para ambientes sem microfone.

try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except Exception:
    VOICE_AVAILABLE = False

class VoiceInterface:
    def __init__(self):
        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.tts = pyttsx3.init()
        else:
            self.recognizer = None
            self.tts = None

    def speak(self, text: str):
        print('[SPEAK]', text)
        if self.tts:
            self.tts.say(text)
            self.tts.runAndWait()

    def listen(self, prompt: str = None) -> str:
        if prompt:
            self.speak(prompt)
        if not VOICE_AVAILABLE:
            return input('Input (texto) -> ')
        with sr.Microphone() as mic:
            audio = self.recognizer.listen(mic, timeout=5)
        try:
            return self.recognizer.recognize_google(audio, language='pt-PT')
        except Exception as e:
            print('STT error:', e)
            return input('Fallback (texto) -> ')

------------------------------------------------------------------
# src/main.py
------------------------------------------------------------------
"""
Ponto de entrada para simular uma sessão de compra.
"""
from sensors import StoreMap, RFIDReader, Cart, ZebraDevice
from agent import AgentAI
from voice import VoiceInterface

import time

def build_demo_store():
    sm = StoreMap()
    # adicionar produtos com posições (x,y) em metros e shelf_level 0/1/2
    sm.add_product('tag001', 'leite', (2.0, 1.0), 1)
    sm.add_product('tag002', 'ovos', (5.5, 1.2), 0)
    sm.add_product('tag003', 'cafe', (3.0, 4.0), 2)
    sm.add_product('tag004', 'acucar', (6.0, 3.5), 1)
    return sm


def run_session():
    store = build_demo_store()
    reader = RFIDReader(store_map=store, range_meters=2.5)
    agent = AgentAI(store, reader)
    zebra = ZebraDevice(sensitivity=0.6)
    cart = Cart('carrinho-001')
    voice = VoiceInterface()

    # posição inicial do cliente (simulada)
    pos = (0.0, 0.0)

    voice.speak('Bem vindo à loja demo. Diga os items que pretende comprar, por exemplo: leite, ovos, café')
    text = voice.listen('Diga a sua lista de compras agora:')
    items = agent.parse_shopping_list(text)
    voice.speak(f'Lista recebida: {items}')

    route = agent.plan_route(pos, items)
    for p, steps in route:
        # instruções para chegar ao produto
        steps_calc, direction = agent.give_directions(pos, p)
        voice.speak(f'Ande {steps_calc} passos na direção {direction} para encontrar {p.name}')
        # simular movimento
        # avançamos para posição do produto (simulação simplificada)
        pos = p.position
        time.sleep(1)
        # agora o utilizador usa o zebra para validar
        voice.speak(f'Agora passe o zebra na prateleira do nível {p.shelf_level} para confirmar {p.name}')
        # simular sweep: normalmente o zebra estaria na mesma posição x,y mas com altura (shelf_level)
        found = zebra.sweep(p, pos, p.shelf_level)
        if found:
            voice.speak('BIP! Produto confirmado. Coloque no carrinho.')
            cart.add(p.uid)
            voice.speak(f'Produto {p.name} adicionado ao carrinho. Carrinho tem agora {len(cart.contents)} itens.')
        else:
            voice.speak('Nada confirmado — tente ajustar a posição ou a altura do zebra.')

    voice.speak('Rota terminada. Obrigado.')

if __name__ == '__main__':
    run_session()

------------------------------------------------------------------
# tests/test_navigation.py
------------------------------------------------------------------
from src.sensors import StoreMap
from src.agent import AgentAI

def test_plan_route():
    sm = StoreMap()
    sm.add_product('t1', 'leite', (1,1), 1)
    sm.add_product('t2', 'cafe', (5,5), 2)
    ri = None
    agent = AgentAI(sm, ri)
    route = agent.plan_route((0,0), ['leite','cafe'])
    assert len(route) == 2

------------------------------------------------------------------
# Instruções de uso em VSCode
------------------------------------------------------------------
1. Criar ambiente virtual
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .\.venv\\Scripts\\activate  # Windows
2. Instalar dependências
   pip install -r requirements.txt
3. Criar a estrutura de ficheiros (src/*.py) copiando o código acima cada bloco para o respetivo ficheiro.
4. Executar
   python src/main.py

------------------------------------------------------------------
# Notas para produção / Google Cloud
------------------------------------------------------------------
Passos gerais para levar a produção (resumo):
- Substituir os módulos simulados por drivers reais:
  * Leitura RFID: usar bibliotecas/hardware do fabricante (ex: Impinj, ThingMagic) ou gateways MQTT
  * Localização em loja: usar BLE beacons, UWB (ultra-wideband) ou triangulação de múltiplos leitores
  * Carrinho: integrar com um microcontrolador (Raspberry Pi / ESP32) que envia eventos por MQTT
- Reescrever AgentAI como serviço:
  * Converter em API (FastAPI) com endpoints para: receber posição do cliente, lista de compras, responder com rota e passos
  * Integrar autenticação e logging
- Deploy:
  * Empacotar como container Docker
  * Usar Google Cloud Run (para API) + Pub/Sub ou IoT Core para mensagens dos dispositivos
  * Usar Cloud SQL / Firestore para catálogo de produtos
  * Usar Cloud Storage para ficheiros e backups
  * Adicionar observabilidade (Cloud Monitoring, Logging)
- Considerações de latência e conectividade:
  * Manter lógica crítica no dispositivo (edge) quando a conectividade falhar
  * Sincronizar catálogo periodicamente

------------------------------------------------------------------
# Próximos passos que eu posso ajudar a concretizar agora
------------------------------------------------------------------
- Gerar os ficheiros prontos (posso criar um repositório local simulado com todos os ficheiros).
- Implementar a API em FastAPI para expor o AgentAI.
- Substituir a simulação por uma integração com um serviço STT/TTS (Google Speech-to-Text, Cloud TTS) e mostrar como autenticar.
- Criar Dockerfile e definição Terraform para deploy no Google Cloud.

Se quiser, eu posso já criar os ficheiros no formato prontos para copiar para VSCode (diga-me se prefere que eu gere os ficheiros aqui no canvas)."""
