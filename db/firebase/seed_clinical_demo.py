"""Seed A1 versionado, sin sobrescribir el fixture histórico ni datos existentes."""

import argparse
import json

import clinical_model
import seed_demo


def seed(client, data):
    seed_demo.emulator_host()
    seed_demo.require(client.project == seed_demo.PROJECT, "Proyecto DEMO incorrecto")
    documents = clinical_model.entries(data)
    seed_demo.require(len(documents) <= 100, "Seed demasiado grande")
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
    refs = [(client.collection(c).document(i), doc) for c, i, doc in documents]

    @firestore.transactional
    def apply(transaction):
        snapshots = [ref.get(transaction=transaction, timeout=10) for ref, _ in refs]
        # También detecta identificaciones previas de pacientes sin reserva (v1).
        for key, patient in data["pacientes"].items():
            query = client.collection("pacientes").where(filter=FieldFilter("identificacion", "==", patient["identificacion"]))
            for snapshot in query.get(transaction=transaction, timeout=10):
                seed_demo.require(snapshot.id == key, "Identificación existente en otro paciente; no se modifica")
        for snapshot, (_, expected) in zip(snapshots, refs):
            seed_demo.require(not snapshot.exists or snapshot.to_dict() == expected, "Conflicto clínico DEMO: documento existente diferente")
        created = 0
        for snapshot, (ref, expected) in zip(snapshots, refs):
            if not snapshot.exists:
                transaction.create(ref, expected)
                created += 1
        return {"created": created, "unchanged": len(refs) - created}

    return apply(client.transaction(max_attempts=3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    data = clinical_model.load_fixture()
    if args.validate_only:
        print(json.dumps({"version": clinical_model.VERSION, "documents": len(clinical_model.entries(data))}))
        return
    client = seed_demo.client_for_emulator()
    try:
        print(json.dumps(seed(client, data), sort_keys=True))
    finally:
        client.close()


if __name__ == "__main__":
    main()
