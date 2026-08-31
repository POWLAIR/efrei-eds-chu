"""Tests de la pseudonymisation RGPD (bonus)."""

import os

os.environ.setdefault("PSEUDO_SALT", "sel-de-test-pour-pytest-1234567890")

from pipeline import pseudonymize as P


def test_hash_deterministe():
    a = P.pseudonymize_patient_id("IPP0000001")
    b = P.pseudonymize_patient_id("IPP0000001")
    assert a == b
    assert len(a) == 16


def test_hash_distinct_par_patient():
    assert P.pseudonymize_patient_id("IPP0000001") != P.pseudonymize_patient_id("IPP0000002")


def test_patients_csv_perd_les_identifiants_directs():
    raw = (
        b"patient_id,nir,nom,prenom,birth_date,sex,region_code\n"
        b"IPP0000001,105077509622423,LEROY,Antoine,2005-07-02,M,75\n"
    )
    out = P.transform_csv_bytes("patients", raw).decode()
    header = out.splitlines()[0]
    assert "nir" not in header and "nom" not in header and "prenom" not in header
    assert "patient_hash" in header and "birth_year" in header
    assert "2005" in out and "2005-07-02" not in out
    assert "LEROY" not in out


def test_jointure_preservee_entre_patients_et_sejours():
    pid = "IPP0000042"
    h_pat = (
        P.transform_csv_bytes(
            "patients",
            f"patient_id,nir,nom,prenom,birth_date,sex,region_code\n{pid},1,A,B,1990-01-01,F,33\n".encode(),
        )
        .decode()
        .splitlines()[1]
        .split(",")[0]
    )
    h_sej = (
        P.transform_csv_bytes(
            "sejours",
            f"stay_id,patient_id,service_code,admission_ts,discharge_ts,admission_mode,discharge_mode\n"
            f"S1,{pid},CARDIO,2026-08-26 10:00:00,,urgence,domicile\n".encode(),
        )
        .decode()
        .splitlines()[1]
    )
    assert h_pat in h_sej


def test_source_non_identifiante_inchangee():
    raw = b"code_cim10,libelle\nI21,Infarctus\n"
    assert P.transform_csv_bytes("referentiels", raw) == raw
