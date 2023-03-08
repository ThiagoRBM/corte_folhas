from datetime import datetime
import os
import json


json_ = open(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "diretorio_folhas.json"
    )
)

DIRETORIO = json.load(json_)["dir"]

HOJE = datetime.now().strftime("%Y%m%d_%H%M%S")

DIRETORIO_PB = os.path.join(DIRETORIO, "preto_branco")
if not os.path.exists(DIRETORIO_PB):
    os.makedirs(DIRETORIO_PB)

DIRETORIO_PB_FOLHA = os.path.join(DIRETORIO_PB, "folhas_recortadas")
if not os.path.exists(DIRETORIO_PB_FOLHA):
    os.makedirs(DIRETORIO_PB_FOLHA)

DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
