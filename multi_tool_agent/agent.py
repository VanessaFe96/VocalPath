import json
import os
import math
from google.adk.agents import Agent
import webbrowser
import html
import json

# Caminhos dos ficheiros
FICHEIRO_LISTA = "lista_compras.json"
FICHEIRO_LOCALIZACOES = "TestDataProductsLocation.json"


def guardar_lista_compras(itens: str) -> dict:
    """Cria e guarda uma lista de compras a partir do texto fornecido pelo utilizador."""
    if not itens.strip():
        return {
            "status": "error",
            "error_message": "Por favor indica pelo menos um produto para adicionar à lista.",
        }

    lista_itens = [item.strip().lower() for item in itens.replace(",", " ").split() if item.strip()]

    with open(FICHEIRO_LISTA, "w") as f:
        json.dump(lista_itens, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "report": f"A tua lista de compras foi guardada com {len(lista_itens)} itens: {', '.join(lista_itens)}."
    }


def carregar_lista_compras() -> dict:
    """Carrega a lista de compras previamente guardada."""
    if not os.path.exists(FICHEIRO_LISTA):
        return {"status": "error", "error_message": "Ainda não tens nenhuma lista de compras guardada."}

    with open(FICHEIRO_LISTA, "r") as f:
        itens = json.load(f)

    return {
        "status": "success",
        "report": f"A tua lista de compras guardada: {', '.join(itens)}.",
        "itens": itens,
    }


def obter_localizacoes_lista() -> dict:
    """Relaciona os itens da lista de compras com as respetivas localizações na loja."""
    if not os.path.exists(FICHEIRO_LISTA):
        return {"status": "error", "error_message": "Não existe nenhuma lista de compras guardada."}

    if not os.path.exists(FICHEIRO_LOCALIZACOES):
        return {"status": "error", "error_message": f"O ficheiro '{FICHEIRO_LOCALIZACOES}' não foi encontrado."}

    with open(FICHEIRO_LISTA, "r") as f:
        lista_itens = json.load(f)

    with open(FICHEIRO_LOCALIZACOES, "r") as f:
        produtos = json.load(f)

    resultados = []
    for item in lista_itens:
        correspondencias = [p for p in produtos if item.lower() in p["nome_produto"].lower()]
        if correspondencias:
            for p in correspondencias:
                resultados.append({
                    "produto": p["nome_produto"],
                    "corredor": p["corredor"],
                    "secção": p["secção"],
                    "prateleira": p["prateleira"],
                    "caixa": p["caixa"],
                    "coordenada_x": p["coordenada_x"],
                    "coordenada_y": p["coordenada_y"],
                })
        else:
            resultados.append({
                "produto": item,
                "erro": "Produto não encontrado na base de dados de localizações."
            })

    texto = "📍 **Localização dos produtos na loja:**\n\n"
    for r in resultados:
        if "erro" in r:
            texto += f"❌ {r['produto'].capitalize()}: {r['erro']}\n"
        else:
            texto += (
                f"🛒 {r['produto']}\n"
                f"   • Corredor: {r['corredor']}\n"
                f"   • Secção: {r['secção']}\n"
                f"   • Prateleira: {r['prateleira']}\n"
                f"   • Caixa: {r['caixa']}\n"
                f"   • Coordenadas: ({r['coordenada_x']}, {r['coordenada_y']})\n\n"
            )

    return {"status": "success", "report": texto, "resultados": resultados}


def gerar_rota_otimizada() -> dict:
    """Gera uma rota otimizada pela loja com base nas coordenadas dos produtos."""
    # Carrega localizações
    localizacoes = obter_localizacoes_lista()
    if localizacoes["status"] == "error":
        return localizacoes

    produtos = [
        p for p in localizacoes["resultados"]
        if "erro" not in p and "coordenada_x" in p and "coordenada_y" in p
    ]

    if not produtos:
        return {"status": "error", "error_message": "Nenhum produto com coordenadas encontrado."}

    # Heurística simples do caixeiro-viajante (Nearest Neighbor)
    rota = []
    visitados = set()
    atual = produtos[0]
    rota.append(atual)
    visitados.add(atual["produto"])

    while len(visitados) < len(produtos):
        proximos = [
            p for p in produtos if p["produto"] not in visitados
        ]
        if not proximos:
            break

        # Escolhe o produto mais próximo
        proximo = min(
            proximos,
            key=lambda p: math.dist(
                (atual["coordenada_x"], atual["coordenada_y"]),
                (p["coordenada_x"], p["coordenada_y"])
            ),
        )
        rota.append(proximo)
        visitados.add(proximo["produto"])
        atual = proximo

    # Formata a rota
    texto = "🚶 **Rota otimizada dentro da loja:**\n\n"
    for i, p in enumerate(rota, start=1):
        texto += (
            f"{i}. 🛒 {p['produto']}\n"
            f"   → Corredor: {p['corredor']} | Secção: {p['secção']}\n"
            f"   → Coordenadas: ({p['coordenada_x']}, {p['coordenada_y']})\n\n"
        )

    texto += "💡 Dica: segue a ordem acima para percorrer o menor trajeto possível dentro da loja."

    return {"status": "success", "report": texto, "rota": rota}


#Teste Vanessa
def mostrar_rota_visual() -> dict:
    """Desenha a planta da loja e gera instruções passo a passo apenas para os produtos guardados na lista de compras."""
    import os, json, math, webbrowser

    # Verificações básicas
    if not os.path.exists(FICHEIRO_LISTA):
        return {"status": "error", "error_message": "Não existe nenhuma lista de compras guardada."}
    if not os.path.exists(FICHEIRO_LOCALIZACOES):
        return {"status": "error", "error_message": f"O ficheiro '{FICHEIRO_LOCALIZACOES}' não foi encontrado."}

    # Carregar dados
    with open(FICHEIRO_LISTA, "r", encoding="utf-8") as f:
        lista_itens = [i.lower().strip() for i in json.load(f)]
    with open(FICHEIRO_LOCALIZACOES, "r", encoding="utf-8") as f:
        produtos = json.load(f)

    # Filtrar produtos que estão na lista guardada
    selecionados = [
        p for p in produtos
        if any(item in p["nome_produto"].lower() for item in lista_itens)
    ]

    if not selecionados:
        return {"status": "error", "error_message": "Nenhum produto da tua lista foi encontrado na base de dados."}

    # Calcular rota otimizada (heurística do vizinho mais próximo)
    rota = []
    visitados = set()
    atual = selecionados[0]
    rota.append(atual)
    visitados.add(atual["nome_produto"])
    while len(visitados) < len(selecionados):
        proximos = [p for p in selecionados if p["nome_produto"] not in visitados]
        if not proximos:
            break
        proximo = min(
            proximos,
            key=lambda p: math.dist(
                (atual["coordenada_x"], atual["coordenada_y"]),
                (p["coordenada_x"], p["coordenada_y"])
            )
        )
        rota.append(proximo)
        visitados.add(proximo["nome_produto"])
        atual = proximo

    # Gerar instruções passo a passo
    instrucoes = []
    for i in range(len(rota) - 1):
        x1, y1 = rota[i]["coordenada_x"], rota[i]["coordenada_y"]
        x2, y2 = rota[i + 1]["coordenada_x"], rota[i + 1]["coordenada_y"]
        dx, dy = x2 - x1, y2 - y1
        distancia = math.sqrt(dx**2 + dy**2)
        angulo = math.degrees(math.atan2(dy, dx))
        if -45 <= angulo <= 45:
            direcao = "siga em frente"
        elif 45 < angulo <= 135:
            direcao = "vire à esquerda"
        elif -135 <= angulo < -45:
            direcao = "vire à direita"
        else:
            direcao = "inverta a direção"
        instrucoes.append(f"{i+1}. {direcao.capitalize()} durante {distancia:.1f} metros até chegar a {rota[i+1]['nome_produto']}.")

    instrucoes_texto = "🗣️ **Instruções passo a passo:**\n\n" + "\n".join(instrucoes)

    # Criar o HTML (rota apenas com produtos da lista)
    html_path = os.path.abspath("rota_visual.html")
    html_content = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Mapa da Loja - Rota Otimizada</title>
<style>
body {{
  font-family: Arial, sans-serif;
  text-align: center;
  background: #f8f9fa;
}}
canvas {{
  background: white;
  border: 1px solid #ccc;
  margin-top: 20px;
  border-radius: 8px;
}}
</style>
</head>
<body>
<h2>🛒 Rota Otimizada na Loja</h2>
<p>Mostrando o percurso entre {len(rota)} produtos da tua lista de compras.</p>
<canvas id="mapa" width="600" height="600"></canvas>

<script>
const rota = {json.dumps(rota, ensure_ascii=False)};
const canvas = document.getElementById("mapa");
const ctx = canvas.getContext("2d");
const scale = 10;

function desenhar(pos=0, frac=0) {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Grelha leve
  ctx.strokeStyle = "#eee";
  for (let i = 0; i <= 50; i++) {{
    ctx.beginPath(); ctx.moveTo(i * scale, 0); ctx.lineTo(i * scale, 50 * scale); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i * scale); ctx.lineTo(50 * scale, i * scale); ctx.stroke();
  }}

  // Linha azul da rota
  ctx.beginPath();
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  rota.forEach((p, i) => {{
    const x = p.coordenada_x * scale, y = p.coordenada_y * scale;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }});
  ctx.stroke();

  // Pontos verdes
  rota.forEach((p) => {{
    const x = p.coordenada_x * scale, y = p.coordenada_y * scale;
    ctx.beginPath(); ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fillStyle = "#22c55e"; ctx.fill();
    ctx.fillStyle = "#333"; ctx.font = "10px Arial";
    ctx.fillText(p.nome_produto, x + 8, y - 8);
  }});

  // Ponto vermelho em movimento
  if (pos < rota.length - 1) {{
    const p1 = rota[pos], p2 = rota[pos + 1];
    const x1 = p1.coordenada_x * scale, y1 = p1.coordenada_y * scale;
    const x2 = p2.coordenada_x * scale, y2 = p2.coordenada_y * scale;
    const x = x1 + (x2 - x1) * frac;
    const y = y1 + (y2 - y1) * frac;
    ctx.beginPath(); ctx.arc(x, y, 8, 0, 2 * Math.PI);
    ctx.fillStyle = "red"; ctx.fill();
  }} else {{
    const last = rota[rota.length - 1];
    ctx.beginPath(); ctx.arc(last.coordenada_x * scale, last.coordenada_y * scale, 8, 0, 2 * Math.PI);
    ctx.fillStyle = "red"; ctx.fill();
  }}
}}

let passo = 0;
let frac = 0;
function animar() {{
  frac += 0.01;
  if (frac >= 1) {{ frac = 0; passo++; }}
  desenhar(passo, frac);
  if (passo < rota.length - 1) requestAnimationFrame(animar);
}}

desenhar();
setTimeout(() => animar(), 1000);
</script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    webbrowser.open(f"file://{html_path}")

    return {
        "status": "success",
        "report": f"🗺️ Mapa e instruções gerados apenas para os produtos da tua lista!\n\n{instrucoes_texto}",
        "instrucoes": instrucoes,
        "rota": rota
    }


root_agent = Agent(
    name="assistente_compras",
    model="gemini-2.0-flash",
    description="Agente em português de Portugal que ajuda o utilizador a criar listas de compras e gerar uma rota otimizada na loja.",
    instruction=(
        "És um assistente útil e simpático que ajuda o utilizador a criar e gerir listas de compras, "
        "encontrar os produtos na loja e calcular a rota mais eficiente entre eles. "
        "Responde sempre em português de Portugal." 
        "Mal abra o agente quero que digas o que sabes fazer sem eu ter de dizer nada"
    ),
    tools=[
        guardar_lista_compras,
        carregar_lista_compras,
        obter_localizacoes_lista,
        gerar_rota_otimizada,
        mostrar_rota_visual, 
    ],
)

