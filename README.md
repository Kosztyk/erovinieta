![logo](https://github.com/user-attachments/assets/8d4b31d0-f312-4465-8216-3c5cc43dad20)

# CNAIR eRovinieta - Integrare pentru Home Assistant 🏠🇷🇴

Această integrare pentru Home Assistant oferă **monitorizare completă** pentru utilizatorii eRovinieta, permițându-le să obțină date despre vehiculele care dețin o rovinietă valabilă (vehicul pentru care a fost achitată rovinieta din contul său), tranzacțiile realizate și alte informații importante, direct din aplicația Home Assistant. 🚀

## 🌟 Caracteristici

### Senzor `Date utilizator`:
  - **🔍 Informații detaliate despre utilizator**:
      - Afișează detalii complete ale utilizatorului din contul CNAIR eRovinieta.
  - **📊 Atribute disponibile**:
      - **Nume complet**: Numele și prenumele utilizatorului.
      - **CNP**: CNP-ul utilizatorului.
      - **Telefon de contact**: Telefonul de contact.
      - **Email utilizator**: Emailul asociat contului.
      - **Acceptă corespondența**: Dacă utilizatorul acceptă corespondența din partea CNAIR.
      - **Adresă**: Adresa completă a utilizatorului.
      - **Localitate și Județ**: Locația detaliată a utilizatorului.



## Senzor `Vehicul`:
  - **🔍 Monitorizare Vehicul**:
      - Afișează detalii complete despre vehiculul care deține o rovinietă valabilă (vehicul pentru care a fost achitată rovinieta din contul său).
  - **📊 Atribute disponibile**:
      - **Număr înmatriculare**: Numărul de înmatriculare al vehiculului.
      - **VIN**: Numărul de serie (VIN) al vehiculului.
      - **Seria certificatului**: Seria certificatului vehiculului.
      - **Țara**: Țara vehiculului.
      - **Categorie vignietă**: Categorie vignietă asociată vehiculului.
      - **Data început vignietă**: Data începerii valabilității vignietei.
      - **Data sfârșit vignietă**: Data expirării vignietei.



## Senzor `Raport tranzacții`:
  - **📊 Monitorizare tranzacții**:
      - Afișează un raport detaliat al tranzacțiilor realizate.
  - **📊 Atribute disponibile**:
      - **Număr facturi**: Numărul total al facturilor.
      - **Suma totală plătită**: Suma totală plătită pentru tranzacțiile efectuate.
      - **Perioadă analizată**: Perioada de timp pentru care sunt adunate tranzacțiile.
      - **Suma totală plătită**: Suma totală a tranzacțiilor înregistrate.


## Senzor `Restanțe treceri pod`:
  - **📊 Monitorizare treceri pod**:
      - Indică dacă există treceri de pod neplătite din ultimele 24 de ore.
  - **📊 Atribute disponibile**:
      - **Număr treceri neplătite**: Numărul total al trecerilor de pod neplătite din ultimele 24 de ore.

**🔍 Atribut principal**:  
- **Da**: În cazul în care există cel puțin o trecere de pod neplătită.  
- **Nu**: În cazul în care nu există nicio trecere de pod neplătită.


## Senzor `Sold peaje neexpirate`:
  - **📊 Monitorizare sold peaje neexpirate**:
      - Afișează valoarea totală a soldului pentru peajele neexpirate.
  - **📊 Atribute disponibile**:
      - **Sold peaje neexpirate**: Valoarea totală a soldului pentru peajele neexpirate.

---

## ⚙️ Configurare

## 🛠️ Interfața UI:
1. Adaugă integrarea din meniul **Setări > Dispozitive și Servicii > Adaugă Integrare**.
2. Introdu datele contului eRovinieta:
   - **Nume utilizator**: username-ul contului tău eRovinieta.
   - **Parolă**: parola asociată contului tău.
   - **Interval de actualizare**: Intervalul de actualizare în secunde (implicit: 3600 secunde).
   - **Istoric tranzacții**: Selectează câți ani de tranzacții dorești să aduci (valoare implicită: 2 ani).
3. Apasă **Salvează** pentru a finaliza configurarea.

## Observații:
- Asigură-te că ai introdus corect datele de autentificare.
- Dacă vrei să aduci tranzacțiile pentru o perioadă mai lungă de timp, selectează un număr mai mare de ani în configurare.

---

## 🚀 Instalare

## 💡 Instalare prin HACS:
1. Adaugă [depozitul personalizat](https://github.com/cnecrea/erovinieta) în HACS. 🛠️
2. Caută integrarea **CNAIR eRovinieta** și instaleaz-o. ✅
3. Repornește Home Assistant și configurează integrarea. 🔄

## ✋ Instalare manuală:
1. Clonează sau descarcă [depozitul GitHub](https://github.com/cnecrea/erovinieta). 📂
2. Copiază folderul `custom_components/erovinieta` în directorul `custom_components` al Home Assistant. 🗂️
3. Repornește Home Assistant și configurează integrarea. 🔧

---

## ✨ Exemple de utilizare

### 🔔 Automatizare pentru expirarea rovinietei:
Creează o automatizare pentru a primi notificări când rovinieta expira în 10 zile.

```yaml
alias: Notificare expirare rovinieta vehicul
description: Notificare atunci când rovinieta expiră în 10 zile
mode: single
triggers:
  - entity_id: sensor.erovinieta_vehicul_[nr_inmatriculare]
    attribute: Expiră peste (zile)
    below: 10
    trigger: numeric_state
conditions: []
actions:
  - data:
      title: Rovinieta expira
      message: >-
        Rovinieta vehiculului cu numărul de înmatriculare {{
        states('sensor.erovinieta_vehicul_[nr_inmatriculare]') }} va expira în 10 zile!
    action: notify.notify

```

## 🔍 Card pentru Dashboard:
Afișează datele despre utilizator, vehicul și tranzacții pe interfața Home Assistant.

```yaml
type: entities
title: Monitorizare eRovinieta
entities:
  - entity: sensor.erovinieta_date_utilizator
    name: Date Utilizator
  - entity: sensor.erovinieta_vehicul_[nr_inmatriculare]
    name: Vehicul
  - entity: sensor.erovinieta_raport_tranzactii
    name: Raport tranzacții
```

---

## ☕ Susține dezvoltatorul

Dacă ți-a plăcut această integrare și vrei să sprijini munca depusă, **invită-mă la o cafea**! 🫶  
Nu costă nimic, iar contribuția ta ajută la dezvoltarea viitoare a proiectului. 🙌  

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Susține%20dezvoltatorul-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/cnecrea)

Mulțumesc pentru sprijin și apreciez fiecare gest de susținere! 🤗

--- 


## 🧑‍💻 Contribuții

Contribuțiile sunt binevenite! Simte-te liber să trimiți un pull request sau să raportezi probleme [aici](https://github.com/cnecrea/erovinieta/issues).
