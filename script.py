import utils
import settings

utils.corta_limpa_img_bruta(settings.DIRETORIO)

utils.calcula_infos(
    settings.DIRETORIO_PB_FOLHA,
    "pb_limpa_sem_faixa",
    settings.DIRETORIO,
)
