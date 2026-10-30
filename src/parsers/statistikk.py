"""Beregner statistikk per spiller ut fra kamphendelsene."""

import numpy as np
import pandas as pd


def sortere_statistikk_utespillere(kamphendelser: pd.DataFrame) -> pd.DataFrame:
    # Lag hjelpekolonner med 0 eller 1 for hver statistikktype
    kamphendelser["Mål"] = np.where(
        kamphendelser["Type"] == "Målscorer",
        1,
        np.nan,
    )
    kamphendelser["Assist"] = np.where(
        kamphendelser["Type"] == "Assist",
        1,
        np.nan,
    )
    kamphendelser["2M utvisning"] = np.where(
        (kamphendelser["Hendelse"] == "2M utvisning")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )
    kamphendelser["2+10M utvisning"] = np.where(
        (kamphendelser["Hendelse"] == "2+10M utvisning")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )
    kamphendelser["Kampstraff"] = np.where(
        (kamphendelser["Hendelse"] == "Kampstraff")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )

    # Grupper på spillerne (Nr og Navn) og summer opp hendelsene
    utespiller_stat: pd.DataFrame = (
        kamphendelser.groupby(["Nr", "Navn", "Lag"])[
            ["Mål", "Assist", "2M utvisning", "2+10M utvisning", "Kampstraff"]
        ]
        .sum()
        .reset_index()
    )

    # Vi filtrerer ut rader der spilleren ikke har gjort noen av delene (for å unngå keepere her)
    # og sorterer etter flest poeng (mål + assist)
    # utespiller_stat["Poeng"] = utespiller_stat["Mål"] + utespiller_stat["Assist"]
    # utespiller_stat = utespiller_stat[
    #     (utespiller_stat["Poeng"] > 0) | (utespiller_stat["2M utvisning"] > 0)
    # ].sort_values(by="Poeng", ascending=False)

    return utespiller_stat


def sortere_statistikk_keepere(kamphendelser: pd.DataFrame) -> pd.DataFrame:
    # Keepere er registrert som 'Type' == 'Målvakt'
    df_keeper: pd.DataFrame = kamphendelser[kamphendelser["Type"] == "Målvakt"].copy()

    # Et 'Skudd' betyr en redning for målvakten
    df_keeper["Redning"] = np.where(df_keeper["Hendelse"] == "Skudd", 1, np.nan)

    # Et 'Mål' eller 'Straffeslag' (som gikk inn) betyr mål imot
    df_keeper["Innsluppet"] = np.where(
        df_keeper["Hendelse"].isin(["Mål", "Straffeslag"]), 1, np.nan
    )

    # Grupper per målvakt for å telle skudd og redninger
    keeper_stat: pd.DataFrame = (
        df_keeper.groupby(["Nr", "Navn", "Lag"])
        .agg(Redninger=("Redning", "sum"), Innsluppet=("Innsluppet", "sum"))
        .reset_index()
    )

    return keeper_stat


def legg_til_stats_utespillere(
    spillere: pd.DataFrame, stats: pd.DataFrame
) -> pd.DataFrame:
    if "2M utvisning" not in stats:
        stats["2M utvisning"] = np.nan
    if "2+10M utvisning" not in stats:
        stats["2+10M utvisning"] = np.nan
    if "Kampstraff" not in stats:
        stats["Kampstraff"] = np.nan

    spillere["DraktNr"] = pd.to_numeric(spillere["DraktNr"], errors="coerce")
    stats["Nr"] = pd.to_numeric(stats["Nr"], errors="coerce")

    spillere["Navn_clean"] = spillere["Navn"].str.strip().str.lower()
    stats["Navn_clean"] = stats["Navn"].str.strip().str.lower()

    df_sammenslått: pd.DataFrame = pd.merge(
        spillere,
        stats[
            [
                "Nr",
                "Navn_clean",
                "Mål",
                "Assist",
                "2M utvisning",
                "2+10M utvisning",
                "Kampstraff",
            ]
        ],
        left_on=["DraktNr", "Navn_clean"],
        right_on=["Nr", "Navn_clean"],
        how="left",
    )

    df_sammenslått = df_sammenslått.drop(columns=["Nr", "Navn_clean"])

    return df_sammenslått


def legg_til_stats_keepere(spillere: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    if "Redninger" not in stats:
        stats["Redninger"] = np.nan
    if "Innsluppet" not in stats:
        stats["Innsluppet"] = np.nan

    spillere["Målvakt"] = spillere["Posisjon/Funksjon"].str.contains(
        "Målvakt", case=False, na=False
    )

    spillere["DraktNr"] = pd.to_numeric(spillere["DraktNr"], errors="coerce")
    stats["Nr"] = pd.to_numeric(stats["Nr"], errors="coerce")

    spillere["Navn_clean"] = spillere["Navn"].str.strip().str.lower()
    stats["Navn_clean"] = stats["Navn"].str.strip().str.lower()

    df_sammenslått: pd.DataFrame = pd.merge(
        spillere,
        stats[["Nr", "Navn_clean", "Redninger", "Innsluppet"]],
        left_on=["DraktNr", "Navn_clean"],
        right_on=["Nr", "Navn_clean"],
        how="left",
    )

    df_sammenslått = df_sammenslått.drop(columns=["Nr", "Navn_clean"])

    tall_kolonner = [
        "Mål",
        "Assist",
        "2M utvisning",
        "2+10M utvisning",
        "Kampstraff",
        "Redninger",
        "Innsluppet",
    ]
    df_sammenslått[tall_kolonner] = df_sammenslått[tall_kolonner].fillna(0).astype(int)

    # Sørg for at Målvakt-kolonnen er en ren True/False (ikke NaN)
    df_sammenslått["Målvakt"] = df_sammenslått["Målvakt"].fillna(False).astype(bool)

    return df_sammenslått
