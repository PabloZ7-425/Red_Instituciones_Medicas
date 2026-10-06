from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class InstitutionConfig:
    slug: str
    name: str
    engine: str


class Institution(Enum):
    HOSPITAL = InstitutionConfig("hospital", "Hospital general", "PostgreSQL")
    PEDIATRICO = InstitutionConfig("pediatrico", "Centro medico pediatrico", "MySQL")
    LABORATORIO = InstitutionConfig("laboratorio", "Laboratorio clinico", "MongoDB")
    ODONTOLOGICA = InstitutionConfig("odontologica", "Clinica odontologica", "Firestore")

    @classmethod
    def from_slug(cls, slug):
        for institution in cls:
            if institution.value.slug == slug:
                return institution
        raise ValueError(f"Institucion no valida: {slug}")
