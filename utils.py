import glob
import cv2
import numpy as np
from skimage import measure
import os
import settings
import matplotlib.pyplot as plt
import re
from PIL import Image
import pandas as pd


def get_folhas_caminho(diretorio):
    """Funcao que pega os caminhos dos arquivos com as folhas escaneadas.
    Recebe uma string com o diretorio onde estao as fotos
    """
    arqs = glob.glob(f"{diretorio}/*.jpg")

    return arqs


def abre_img(caminhos):
    """Funcao que abre uma imagem, e transforma em P&B"""
    if isinstance(caminhos, str):
        caminhos = [caminhos]

    for caminho in caminhos:
        imagem = cv2.imread(caminho)

    return imagem


def get_dpi(diretorio):
    """Funcao que salva os dpis das imagens e um arquivo '.csv' para ser usado
    no cálculo da área
    """
    caminhos = get_folhas_caminho(diretorio)
    dpis = []
    for caminho in caminhos:
        imagem = Image.open(caminho)
        dpi = imagem.info["dpi"][0]
        dpis.append([caminho, dpi])

    infos = pd.DataFrame(
        dpis,
        columns=[
            "caminho",
            "dpi",
        ],
    )

    infos.to_csv(
        os.path.join(diretorio, "imgs_dpi.csv"),
        sep=";",
        index=False,
    )

    return dpis


def remove_escala(img):
    """Funcao que remove a escala usada para escanear a figura. Recebe uma
    imagem e a binariza. Após a binarização, a função deteca as diferenças mais
    abruptas entre uma região branca e escura.
    Essa região provavelmente é a escala, porque em folhas, que tem formas
    'orgânicas' e não retas, a transição é mais suave.
    A detecção de transiçẽos brutas é feita considerando cada pixel da largura
    da imagem como uma coluna e somando os valores das linhas (ou seja, o
    comprimento).
    Retorna a imagem colorida, sem a régua
    """

    shape = img.shape
    im_bin = img[5:, :, 2] / 255 < 0.48
    im_bin = im_bin.astype(np.uint8)
    kernel = np.ones((7, 7), np.uint8)
    dilation = cv2.dilate(im_bin, kernel, iterations=1)

    cols = np.sum(dilation, axis=0)  # aqui, fazendo a soma de linhas

    max = cols.argmax()
    # min = cols[max : int(len(cols) * 0.35)].argmin() + max
    # breakpoint()
    espaco_apos_regua = cols < shape[1] * 0.1
    try:
        fim_regua = np.where(espaco_apos_regua[max:] == True)[0][0] + max
    except IndexError:
        breakpoint()
    #  acima, pegando o primeiro valor que tenha soma < 10% da altura da figura
    #  e considera como o final da régua, após o valor máximo

    # breakpoint()

    if (max < shape[1] * 0.35) and (
        cols[max] > cols[int(max - (shape[1] * 0.05))] * 1.6
    ):
        # tentativa de "detectar" uma régua / escala no lado direito:
        # 1. se o valor máximo da soma das linhas da imagem estiver em um ponto
        # menor que 35% da largura da imagem **E**
        # 2. Se a soma de linhas atrás desse valor máximo for 60% menor que ele

        img_cortada = img[:, fim_regua:, :]

        return img_cortada

    else:
        return img


def plota(img):
    """FUncao simples para plotar uma imagem. Estava muito chato
    copiar e colar as 3 linhas de código toda hora.
    """
    plt.imshow(img)
    plt.axis("off")
    plt.show()

    return 1


def salva_img(img, diretorio, nome_img):
    """Funcao que salva o arquivo gerado.
    Recebe uma imagem, o nome com que a imagem será salva e o diretorio em que
    ela será salva
    """

    cv2.imwrite(
        os.path.join(diretorio, f"{nome_img}"),
        img,
        [cv2.IMWRITE_JPEG_QUALITY, 100],
    )

    return 1


def hard_binary(img, val):
    """Funcao que recebe uma imagem e a binariza usando um valor fixo na
    banda verde (por isso o nome "hard").
    Usa a banda verde para isso.
    """
    banda_verde = img[:, :, 1]
    binarizada = banda_verde / 255 < val
    binarizada = binarizada.astype(np.uint8) * 255

    return binarizada


def label_limpa(img, arq):
    """Funcao que numera os objetos da imagem binária e a limpa.
    A limpeza é feita:
    1. retirando onjetos muito pequenos, que provavelmente
    são sugeira
    2. retirando objetos com formas pouco prováveis de serem biológicas,
    considerando por exemplo a razão entre eixo mais comprido e mais curto
    """
    props = measure.regionprops(img)
    objs = list(range(1, img.max() + 1))
    area_imagem = img.shape[0] * img.shape[1]

    #  retirando sujeiras (obejtos com área pequena)
    areas_objetos = [obj.area for obj in props]
    zip_img = list(zip(objs, areas_objetos))
    filtro_area = [
        obj[0] for obj in zip_img if obj[1] > int(area_imagem * 0.01)
    ]

    img_limpa_1 = np.zeros_like(img)
    mask = np.isin(img, filtro_area)
    img_limpa_1[mask] = img[mask]

    # retirando objetos com formatos "estranhos" (razão entre eixos alta)
    img_limpa_2 = measure.label(img_limpa_1)
    props_limpa = measure.regionprops(img_limpa_2)
    eixo_maior = [int(obj.axis_major_length) for obj in props_limpa]
    eixo_menor = [int(obj.axis_minor_length) for obj in props_limpa]
    razao_eixos = [
        int(maior / menor)
        for maior, menor in zip(eixo_maior, eixo_menor)
        if int(maior / menor) > 10
    ]

    if len(razao_eixos) > 0:
        #  se tiver algum objeto com razão eixo maior / eixo menor > 10,
        #  retira ele
        img_limpa_2 = np.zeros_like(img_limpa_1)
        mask = np.isin(img_limpa_1, razao_eixos, invert=True)
        img_limpa_2[mask] = img_limpa_1[mask]

        salva_img(img_limpa_2 * 255, settings.DIRETORIO_PB, f"{arq}_pb.jpg")

        return img_limpa_2 * 255

    else:
        salva_img(img_limpa_1 * 255, settings.DIRETORIO_PB, f"{arq}_pb.jpg")

        return img_limpa_1 * 255


def corta_bbox_colorida(img_pb, img_colorida, especie_individuo, dpi_original):
    """Funcao que pega uma imagem binarizada já sem régua e limpa, identifica
    os objetos nela e corta cada objeto da imagem de acordo com a
    bounding box dele.
    Recebe uma imagem binarizada, uma imagem colorida e um sufixo representando
    a espécie e número do indivíduo da imagem (que é o nome do arquivo mesmo).
    Recebe o valor de DPI da imagem escaneada original, que foi obtido
    com a função get_dpi. Coloquei o dpi no nome da própria imagem para
    ficar fácil saber qual é ele na hora de calcular a área da folha
    Retorna uma lista de imagens
    """

    labels = measure.label(img_pb)
    props = measure.regionprops(labels)
    objs = list(np.unique(labels))

    bbox_objetos = [obj.bbox for obj in props]

    zip_img = list(zip(objs[1:], bbox_objetos))
    # bbox ao redor de cada objeto é dado como:
    # (min_row, min_col, max_row, max_col)

    folhas = []
    for obj, bbox in zip_img:
        arq = f"{especie_individuo}_folha_{obj}"
        min_y, min_x, max_y, max_x = bbox  # pega as coord. do bbox

        folha = img_colorida[
            min_y:max_y, min_x:max_x
        ]  # recorta a img colorida
        folha = cv2.copyMakeBorder(
            folha, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=(255, 255, 255)
        )
        folhas.append((arq, folha))

        salva_img(
            folha, settings.DIRETORIO_PB_FOLHA, f"{arq}_{dpi_original}dpi.jpg"
        )
        # cv2.imwrite(
        #     os.path.join(
        #         settings.DIRETORIO_PB_FOLHA,
        #         f"{arq}.jpg",
        #     ),
        #     folha,
        # )

    return folhas


def otsu_binary(img_cortada):
    """Funcao que binariza a imagem pelo método otsu"""

    binarizadas = []
    for arq, img in img_cortada:

        banda_verde = img[:, :, 2]
        _, binarizada = cv2.threshold(banda_verde, 110, 255, cv2.THRESH_OTSU)

        binarizadas.append((arq, 255 - binarizada))

        # salva_img(
        #     255 - binarizada, settings.DIRETORIO_PB_FOLHA, f"{arq}_pb.jpg"
        # )

        # cv2.imwrite(
        #     os.path.join(
        #         settings.DIRETORIO_PB_FOLHA,
        #         f"{arq}_pb.jpg",
        #     ),
        #     255 - binarizada,
        # )

    return binarizadas


def limpa_otsu(img_otsu):
    """Funcao que recebe uma lista com as imagens das folhas cortadas e
    binarizadas pelo método otsu e as limpa, para remover sujeiras
    """

    kernel = np.ones((3, 3), np.uint8)

    folhas = []
    for arq, img in img_otsu:

        img = cv2.erode(img, kernel, iterations=2)
        img = cv2.dilate(img, kernel, iterations=2)

        labels = measure.label(img)
        objs = list(range(1, labels.max() + 1))

        props = measure.regionprops(labels)
        maior_eixo_objetos = [obj.axis_major_length for obj in props]
        zip_img = list(zip(objs, maior_eixo_objetos))

        folha_obj = sorted(zip_img, key=lambda x: x[1], reverse=True)[0]
        # pega o maior objeto da imagem recortada

        folha = np.where(labels != int(folha_obj[0]), 0, 1)
        # o que não for o objeto mais comprido é substituído por 0
        # o objeto principal da imagem é o que tem o maior eixo, porque
        # será uma folha inteira e com o bounding box centralizada nela
        # usar a área da folha para definir o objeto principal nem sempre
        # funciona

        folhas.append((arq, folha))

        # salva_img(
        #     folha * 255, settings.DIRETORIO_PB_FOLHA, f"{arq}_pb_limpa.jpg"
        # )
        # cv2.imwrite(
        #     os.path.join(
        #         settings.DIRETORIO_PB_FOLHA,
        #         f"{arq}_pb_limpa.jpg",
        #     ),
        #     folha * 255,
        # )

    return folhas


def remove_faixa_superior(imgs, dpi_original):
    """Algumas folhas estavam próximas ao topo da folha A4 quando foram
    escaneadas e a sombra da luz do escaner estavam sendo confundidas
    com a folha. Não aconteceu muito, mas achei melhor fazer uma função
    para remover essa faixa, quando ela existe
    Recebe o valor de DPI da imagem escaneada original, que foi obtido
    com a função get_dpi. Coloquei o dpi no nome da própria imagem para
    ficar fácil saber qual é ele na hora de calcular a área da folha
    """

    imgs_sem_faixa = []
    for arq, img in imgs:
        shape = img.shape

        cols = np.sum(img, axis=1)
        max = int(shape[1] * 0.026)
        faixa = cols[:max]  # procura pela faixa em 2,5% da altura dela
        faixa_max = np.argmax(
            faixa
        )  # pega o maior valor (considerado a faixa)
        faixa_min = (
            np.argmin(faixa[faixa_max:]) + faixa_max
        )  # corta até o mínimo

        if (cols[faixa_max] >= shape[1] * 0.3) and cols[faixa_max] > cols[
            faixa_min
        ]:
            # verifica se nessa faixa existe algum valor >= 30% da img E
            # de o valor de "faixa_min" for MENOR ou igual a "faixa_max".
            # Caso seja MENOR, é assumido que tem um objeto maior e depois
            # começa a folha

            img_sem_faixa = img[faixa_min:, :]

            imgs_sem_faixa.append((arq, img_sem_faixa))

            salva_img(
                img_sem_faixa * 255,
                settings.DIRETORIO_PB_FOLHA,
                f"{arq}_pb_limpa_sem_faixa_{dpi_original}dpi.jpg",
            )
            # cv2.imwrite(
            #     os.path.join(
            #         settings.DIRETORIO_PB_FOLHA,
            #         f"{arq}_pb_limpa_sem_faixa.jpg",
            #     ),
            #     img_sem_faixa * 255,
            # )

        else:

            salva_img(
                img * 255,
                settings.DIRETORIO_PB_FOLHA,
                f"{arq}_pb_limpa_sem_faixa_{dpi_original}dpi.jpg",
            )

            imgs_sem_faixa.append((arq, img))

    return imgs_sem_faixa


def corta_limpa_img_bruta(diretorio_img_escaneadas):
    """Funcao que limpa e corta as imagens. Cada folha de cada imagem
    é salva em um arquivo separado e numerada, mantendo o número do indivíduo.
    São criada as seguintes pastas dentro do diretório que foi passado para
    a função:
    1. Diretório com as imagens com todas as folhas em preto e branco
    2. Subdiretório com as folhas coloridas e em preto e branco
    """

    folhas_dpi = get_dpi(diretorio_img_escaneadas)

    for img, dpi in folhas_dpi:

        arq = os.path.basename(img).replace(".jpg", "")

        print(f"iniciando processamento de {arq}")

        img = abre_img(img)

        img_sem_regua = remove_escala(img)

        pb_img = hard_binary(img_sem_regua, 0.52)

        all_labels = measure.label(pb_img)

        fig_limpa = label_limpa(all_labels, arq)

        fig_cortada = corta_bbox_colorida(fig_limpa, img_sem_regua, arq, dpi)

        bin_otsu = otsu_binary(fig_cortada)

        cortada_limpas = limpa_otsu(bin_otsu)

        cortada_sem_faixa = remove_faixa_superior(cortada_limpas, dpi)

        print(f"salva figura {arq}\n\n")

    print("%" * 72)
    print(f"Arquivos salvos em {diretorio_img_escaneadas}")
    print("%" * 72)

    return 1


def get_dpi_from_name(nome_img):
    """Funcao que remove o valor do DPI a partir do nome da imagem"""
    dpi = re.search("([^_]*)$", nome_img).group(0)
    dpi = int(re.search("[0-9]+", dpi).group(0))

    return dpi


def calcula_infos(
    diretorio_folhas, sufixo, diretorio_saida, dpi_imagem_escaneada=200
):
    """Funcao que calcula informacoes da imagem, como área em cm².
    Recebe:
    1. O caminho para o diretóio onde as imagens estão.
    2. O sufixo das imagens, por exemplo, com '_pb_limpa_sem_faixa'
    ele pegará todas as imagens do diretório fornecido,
    que contenham esse sufixo.
    3. O diretório de saída, em que o arquivo '.csv' com as áreas será salvo.
    O separado de colunas usado é o ponto e vírgula.
    4. O dpi com que a imagem foi escaneada.
    Atenção: Conferir esse valor. Coloquei como padrão 200 dpi, mas pode ser
    alterado.
    """
    imgs = get_folhas_caminho(diretorio_folhas)
    # sufixo = "pb_limpa_sem_faixa"
    filtro = [img for img in imgs if bool(re.search(sufixo, img))]
    filtro = [img for img in filtro if bool(re.search("dpi", img))]

    info_folha = []
    for img in filtro:
        # breakpoint()
        dpi_imagem_escaneada = get_dpi_from_name(img)
        arq = os.path.basename(img).replace(".jpg", "")
        print(f"processando {arq}")

        image = Image.open(img)
        dpi = dpi_imagem_escaneada if dpi_imagem_escaneada != 200 else 200
        image = cv2.imread(img, cv2.IMREAD_GRAYSCALE) / 255

        labels = measure.label(image)
        props = measure.regionprops(labels)
        area_folha_pixel = sorted([obj.area for obj in props], reverse=True)[0]
        #  considerando a folha como sendo o maior objeto da imagem, que
        #  já está limpa

        area_folha_cm = round((area_folha_pixel / (dpi / 2.54) ** 2), 3)
        # transformando a área em pixels em área em cm²

        info_folha.append([arq, area_folha_cm, dpi, img])

    infos = pd.DataFrame(
        info_folha,
        columns=[
            "especie_folha",
            "area_folha_cm",
            "dpi_calculo",
            "caminho_img",
        ],
    )

    infos.to_csv(
        os.path.join(diretorio_saida, "areas_calculo.csv"),
        sep=";",
        index=False,
    )

    print(
        f"\nArquivo com as áreas foliares calculadas solvo em:\n\n{os.path.join(diretorio_saida, 'areas_calculo')}\n"
    )

    return infos
