from __future__ import annotations

from abc import ABC, abstractmethod
import logging

import pandas as pd


logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Falha de contrato na etapa de extração.

    Erro nomeado em vez de TypeError/ValueError crus: a DAG consegue separar
    "a fonte quebrou o contrato" (retry adianta) de "o código tem bug" (retry
    só repete a falha), e quem chama captura o que sabe tratar.
    """


class Extractor(ABC):
    schema: tuple[str, ...] = ()

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """coleta os dados da fonte e dfevolve Dataframe cru"""
        ...

    def run(self) -> pd.DataFrame:
        nome =self.__class__.__name__
        logger.info("Iniciando extração: %s", nome)
        df = self.extract()

        if not isinstance(df, pd.DataFrame):
            raise ExtractionError(f"{nome}.extract() deve retornar um DataFrame")

        faltando = set(self.schema) - set(df.columns)
        if faltando:
            raise ExtractionError(
                f"{nome}: colunas ausentes no retorno {sorted(faltando)}"
                )
        if df.empty:
            logger.warning("%s retornou 0 linhas - verifique a fonte", nome)

            
        logger.info("Extração concluída: %s -> %d linhas", nome, len(df))
        return df