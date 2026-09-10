"""Pull set 18's real numbers off CommunityDragon and write them to reference/.

Run `python tft_data.py update` after a patch. It downloads the PBE data, writes
reference/tft_data.json plus the three markdown digests next to it, and prints
every value that moved since the last run -- so a balance patch shows up as a
readable list ("Adaptor (2) ADAPGain: 0.2 -> 0.25") rather than a 70MB blob you
have to go spelunking in.

    python tft_data.py update            # fetch + build + report changes
    python tft_data.py update --refresh  # re-download even if cached
    python tft_data.py build             # rebuild from cache, no network
    python tft_data.py diff              # what would change, without writing

Everything lands in reference/, which is committed: `git diff reference/` is
then a patch-note diff. The raw downloads land in .tft_cache/, which is not.


Where the numbers come from
---------------------------
Four sources, because no single one has everything:

  cdragon/tft/en_us.json    traits, items, and -- once Riot publishes them --
                            champions, complete with ability text and named
                            per-star ability variables. The best source by far,
                            when it has the set.
  map22.bin.json            the set's own record: which characters and traits
                            belong to it, and each unit's cost/tier. Also
                            carries trait values, which cross-check en_us.
  game/characters/*.json    per-unit base stats and raw spell DataValues. The
                            only champion source for a set cdragon hasn't
                            picked up yet.
  tft.stringtable.json      localized ability text, looked up by the tra keys
                            in the character bins.

Two gotchas that are easy to lose an afternoon to:

  * raw.communitydragon.org answers 403 to a request with no User-Agent.
  * Values arrive under hashed keys -- {0412779a} rather than ADAPGain. Two
    mechanisms undo that; see resolve_hash below. Anything still unresolved is
    left as {hash} rather than dropped, so a value never silently disappears.

Champions come from both en_us.json and the bins, merged. For a published set
en_us is the better half by a distance -- it carries the ability description
with its variables already named and split per star level, which is exactly the
shape a champion implementation needs. But a set still in development has only
PVE monsters in that list while its real roster already exists in the bins, so
neither source alone covers both cases.

Data for a set under development is incomplete in ways worth knowing about:
a unit whose spell hasn't been authored yet ships placeholder DataValues
(0/1/2/10 and the like), and set 18's ability text isn't in the string table at
all yet. Both surface as explicit "not published" markers in the output instead
of being quietly omitted, so you can tell "Riot hasn't written this" apart from
"the scraper missed it".

Pass --set/--channel to point this at another set, which is the way to sanity
check it: `python tft_data.py build --set 17 --out /tmp/s17` regenerates the
live set and its numbers can be checked against tactics.tools.
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request

SET_NUMBER = 18
# 18.2 is on PBE and the simulator is pinned to it (see patch_pin.json), so
# the set's own data comes from the pbe channel again and latest -- the live
# 18.1 build -- is the cross-check. Flip both back together when 18.2 ships.
CHANNEL = "pbe"

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, ".tft_cache")
OUT_DIR = os.path.join(HERE, "reference")

CDRAGON = "https://raw.communitydragon.org"

# CDTB's published hash dictionaries. They cover the bin format's structural
# field names; TFT's own gameplay variables mostly aren't in them (see
# resolve_hash).
URL_HASHES = [
    f"{CDRAGON}/data/hashes/lol/hashes.binfields.txt",
    f"{CDRAGON}/data/hashes/lol/hashes.bintypes.txt",
]


def set_key():
    return f"TFTSet{SET_NUMBER}"


def urls():
    """Channel-dependent source URLs.

    The channel is a runtime setting, not a constant, so these are built on
    demand rather than at import.
    """
    base = f"{CDRAGON}/{CHANNEL}"
    return {
        "en_us.json": f"{base}/cdragon/tft/en_us.json",
        "map22.bin.json": f"{base}/game/data/maps/shipping/map22/map22.bin.json",
        "tft.stringtable.json": f"{base}/game/en_us/data/menu/en_us/tft.stringtable.json",
        "character": base + "/game/characters/{name}.cdtb.bin.json",
    }


def cache_dir():
    # Keyed by channel so a --channel live run for cross-checking doesn't
    # overwrite the pbe cache the set is actually built from.
    return os.path.join(CACHE_DIR, CHANNEL)

USER_AGENT = "tftSim-reference-builder (+https://raw.communitydragon.org)"

# Field hashes CDTB's dictionaries don't cover, identified by checking the
# values against units whose numbers are already known. maxMana was confirmed
# against LeBlanc (40) and Cassiopeia (30), both of which match what
# set18champs.py already had.
KNOWN_HASHES = {
    "{726ee5cd}": "maxMana",
}


# ---------------------------------------------------------------- fetching


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(url, dest, refresh=False, quiet=False):
    """Download url to dest, reusing whatever's already cached."""
    if os.path.exists(dest) and not refresh:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.time()
    tmp = dest + ".part"
    with urllib.request.urlopen(request, context=_ssl_ctx(), timeout=600) as response:
        with open(tmp, "wb") as handle:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)
    os.replace(tmp, dest)
    if not quiet:
        size = os.path.getsize(dest) / 1e6
        print(f"  {os.path.basename(dest):<28} {size:6.1f} MB  {time.time()-started:4.1f}s")
    return dest


def cache_age():
    """How old the cached download is, so a report says what it is reporting on.

    "No changes since the last run" means nothing without this: the same
    sentence covers "cdragon has not moved" and "we never asked cdragon".
    """
    marker = os.path.join(cache_dir(), "en_us.json")
    if not os.path.exists(marker):
        return "empty"
    age = time.time() - os.path.getmtime(marker)
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(marker)))
    if age < 3600:
        return f"fetched {stamp} ({int(age // 60)} min ago)"
    if age < 86400:
        return f"fetched {stamp} ({int(age // 3600)} h ago)"
    return f"fetched {stamp} ({int(age // 86400)} days ago -- rerun with --refresh)"


def fetch_all(refresh=False):
    print(f"Fetching {CHANNEL} data from CommunityDragon...")
    source = urls()
    for name in ("en_us.json", "map22.bin.json", "tft.stringtable.json"):
        fetch(source[name], os.path.join(cache_dir(), name), refresh)
    for url in URL_HASHES:
        fetch(url, os.path.join(CACHE_DIR, os.path.basename(url)), refresh)

    # The character bins are per-unit, so the set record has to be parsed first
    # to know which ones to ask for.
    map22 = load_json("map22.bin.json")
    names = set_character_names(map22)
    print(f"  {len(names)} character bins...")
    missing = []
    for name in names:
        dest = os.path.join(cache_dir(), "characters", f"{name}.cdtb.bin.json")
        try:
            fetch(source["character"].format(name=name), dest, refresh, quiet=True)
        except Exception as exc:  # a unit can be listed before its bin exists
            missing.append(f"{name} ({exc})")
    if missing:
        print(f"  {len(missing)} not published yet: {', '.join(missing[:5])}"
              + (" ..." if len(missing) > 5 else ""))


def load_json(name):
    path = os.path.join(cache_dir(), name)
    if not os.path.exists(path):
        sys.exit(
            f"{path} is missing -- run `python tft_data.py update"
            f"{'' if CHANNEL == 'pbe' else ' --channel ' + CHANNEL}` first."
        )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------ hash undoing


def fnv1a(name):
    """CDTB's bin hash: 32-bit FNV-1a over the lowercased name."""
    value = 0x811C9DC5
    for byte in name.lower().encode():
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return f"{{{value:08x}}}"


def load_hash_table():
    """CDTB's published field/type dictionaries, keyed the way the JSON is."""
    table = {}
    for url in URL_HASHES:
        path = os.path.join(CACHE_DIR, os.path.basename(url))
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                digest, _, name = line.strip().partition(" ")
                if name:
                    table.setdefault("{%s}" % digest.lower(), name)
    return table


def desc_hash_table(desc):
    """Recover TFT variable names from the @Tokens@ in a description.

    CDTB's dictionaries barely cover gameplay variables -- ADAPGain isn't in
    them -- but a trait's own description names every variable it uses, in
    markers like `@ADAPGain*100@%` or `@MinUnits@`. Hashing those names back
    reproduces exactly the keys the values arrived under. That recovered all ten
    of Adaptor's and Riftbeast's, which no dictionary lookup could.
    """
    table = {}
    for token in re.findall(r"@([^@]+)@", desc or ""):
        # Markers carry display arithmetic: @CapstoneAD*100@, @Foo/2@.
        name = re.split(r"[*/+\-]", token)[0].strip()
        if name:
            table[fnv1a(name)] = name
    return table


def resolve_hash(key, *tables):
    for table in tables:
        if key in table:
            return table[key]
    return key


def resolve_dict(mapping, *tables):
    """Rename a {hash: value} dict in place-ish, keeping unresolved keys."""
    return {resolve_hash(k, *tables): v for k, v in (mapping or {}).items()}


# --------------------------------------------------------------- traversal


def deref(map22, ref):
    """map22 stores cross-record links as either a path or a {hash} key."""
    if isinstance(ref, str):
        return map22.get(ref)
    return None


def set_record(map22):
    record = map22.get(f"Maps/Shipping/Map22/Sets/{set_key()}")
    if record is None:
        sys.exit(f"map22 has no {set_key()} record -- has the set key changed?")
    return record


def set_character_paths(map22):
    """Every Characters/... path the set's character lists point at."""
    paths = []
    for list_ref in set_record(map22).get("tftCharacterLists", []):
        entry = deref(map22, list_ref) or {}
        for path in entry.get("characters", []):
            if path not in paths:
                paths.append(path)
    return paths


def set_character_names(map22):
    """Bin filenames for the set's characters (Characters/DA_X -> da_x)."""
    return [p.split("/", 1)[-1].lower() for p in set_character_paths(map22)]


def shop_data_by_character(map22):
    """TftShopData records keyed by the character name they describe."""
    shop = {}
    for value in map22.values():
        if isinstance(value, dict) and value.get("__type") == "TftShopData":
            name = value.get("mName")
            if name:
                shop[name] = value
    return shop


# -------------------------------------------------------------- extraction


def extract_traits(en_us):
    """Traits with their per-breakpoint values, variable names restored."""
    entry = next(
        (s for s in en_us.get("setData", []) if s.get("mutator") == set_key()), None
    )
    if entry is None:
        sys.exit(f"en_us.json has no {set_key()} setData entry.")

    traits = []
    for trait in sorted(entry.get("traits", []), key=lambda t: t.get("name") or ""):
        desc = trait.get("desc") or ""
        names = desc_hash_table(desc)
        breakpoints = []
        for effect in trait.get("effects", []):
            max_units = effect.get("maxUnits")
            breakpoints.append(
                {
                    "minUnits": effect.get("minUnits"),
                    # 25000 is the bin's "no upper bound" sentinel.
                    "maxUnits": None if max_units and max_units >= 25000 else max_units,
                    "variables": resolve_dict(effect.get("variables"), names),
                }
            )
        traits.append(
            {
                "apiName": trait.get("apiName"),
                "name": trait.get("name"),
                "desc": desc,
                "breakpoints": breakpoints,
            }
        )
    return traits


def _stat(record, key):
    value = record.get(key)
    if isinstance(value, dict):
        return value.get("baseValue")
    return value


def _spell_objects(char_bin):
    return [
        v
        for v in char_bin.values()
        if isinstance(v, dict) and v.get("__type") == "SpellObject"
    ]


# A spell Riot hasn't authored yet ships the bin template's placeholder
# DataValues. Flagging that beats reporting 0/1/2/10 as if it were balance data.
PLACEHOLDER_DATA_VALUE_NAMES = {"DataValue", "OtherValue"}


def _pick_ability(spells, api_name):
    """Find the unit's actual ability among its SpellObjects.

    A bin holds every spell the unit owns, not just the castable one: basic
    attack variants, crit attacks, and one object per projectile. Kai'Sa has 18,
    of which 17 have no DataValues at all. "The one that isn't the basic attack"
    picks an arbitrary missile and reports the champion as having no data.

    Riot's naming is consistent -- the ability is <CharacterName>Spell -- so
    match that first, then fall back to whichever object actually carries both
    tooltip keys and data values.
    """
    by_name = {(s.get("mScriptName") or ""): s for s in spells}
    for candidate in (f"{api_name}Spell", f"{api_name}_Spell"):
        if candidate in by_name:
            return by_name[candidate]

    def scored(spell):
        inner = spell.get("mSpell") or {}
        tooltip = (inner.get("mClientData") or {}).get("mTooltipData") or {}
        return (bool(tooltip.get("mLocKeys")), len(inner.get("DataValues") or []))

    ranked = sorted(
        (s for s in spells if not (s.get("mScriptName") or "").endswith("BasicAttack")),
        key=scored,
        reverse=True,
    )
    for spell in ranked:
        if any(scored(spell)):
            return spell
    return None


def flatten_formula(parts):
    """Flatten a spell calculation into a list of ratio-times-data-value terms.

    A formula part isn't always one term. Kai'Sa's TotalDamage is a
    SumOfSubPartsCalculationPart wrapping two of them (1.0 x ADDamage plus
    0.01 x APDamage), and reading only the top level yields nothing at all --
    which is how "TotalDamage = None x None" got printed. Recursing over both
    mSubpart and mSubparts covers the shapes TFT actually uses.
    """
    terms = []
    for part in parts or []:
        if not isinstance(part, dict):
            continue
        nested = part.get("mSubparts")
        if isinstance(nested, list):
            terms.extend(flatten_formula(nested))
            continue

        subpart = part.get("mSubpart")
        data_value = (subpart or {}).get("mDataValue") if isinstance(subpart, dict) else None
        if data_value is None:
            data_value = part.get("mDataValue")
        if data_value is None:
            continue
        terms.append(
            {
                "dataValue": data_value,
                "ratio": part.get("mRatio"),
                # A style tag names the stat ("scaleAP"); otherwise the bin's
                # stat enum is all there is, so pass the number through rather
                # than guess at its meaning.
                "scalesWith": part.get("mStyleTagIfScaled")
                or part.get("mStyleTag")
                or (f"stat {part['mStat']}" if "mStat" in part else None),
            }
        )
    return terms


def extract_spell(char_bin, api_name, strings, hashes):
    """The unit's ability: cast time, data values, damage formulas, text."""
    ability = _pick_ability(_spell_objects(char_bin), api_name)
    if ability is None:
        return None

    spell = ability.get("mSpell") or {}
    data_values = {}
    for value in spell.get("DataValues", []):
        name = value.get("name")
        if name:
            data_values[name] = value.get("values")

    tooltip = ((spell.get("mClientData") or {}).get("mTooltipData") or {})
    loc_keys = tooltip.get("mLocKeys") or {}

    calculations = {}
    for key, calc in (spell.get("mSpellCalculations") or {}).items():
        parts = flatten_formula(calc.get("mFormulaParts", []))
        if parts:
            calculations[resolve_hash(key, hashes)] = parts

    placeholder = bool(data_values) and set(data_values) <= PLACEHOLDER_DATA_VALUE_NAMES
    return {
        "script": ability.get("mScriptName"),
        "castTime": spell.get("mCastTime"),
        "dataValues": data_values,
        "dataValuesArePlaceholder": placeholder,
        "calculations": calculations,
        "name": lookup_string(strings, loc_keys.get("keyName")),
        "text": lookup_string(strings, loc_keys.get("keyTooltip")),
    }


def lookup_string(strings, key):
    """Localized text, or a marker saying Riot hasn't published it."""
    if not key:
        return None
    # The string table lowercases its keys; the bins don't.
    value = strings.get(key) or strings.get(key.lower())
    return value if value else f"<not published: {key}>"


def set_prefix(en_us):
    """The namespace this set's assets live under, e.g. DA_ or TFT17_.

    Worth deriving rather than hardcoding: set 18 uses DA_, not the TFT18_ the
    numbering would suggest, and there's no reason to expect set 19 to follow
    either convention. The traits all share it, so it's their common prefix up
    to the last underscore.
    """
    entry = next(
        (s for s in en_us.get("setData", []) if s.get("mutator") == set_key()), None
    )
    names = [t.get("apiName") or "" for t in (entry or {}).get("traits", [])]
    names = [n for n in names if n]
    if not names:
        return f"TFT{SET_NUMBER}_"
    common = os.path.commonprefix(names)
    return common[: common.rfind("_") + 1] or f"TFT{SET_NUMBER}_"


def display_name(api_name, prefix=""):
    """A readable name from the api name, for when the string table has none.

    Set 18's display names aren't in the string table yet, and a table of 100
    rows all reading "<not published: DisplayName_TFT18_X>" is useless to look a
    champion up in. The api name already carries the name, just wrapped in set
    scaffolding: DA_18_Akali_AD -> Akali (AD), DA_Gromp18_AP -> Gromp (AP).
    The AD/AP suffix is kept because it's meaningful -- it's the version an
    Adaptor unit starts on.
    """
    name = api_name[len(prefix):] if prefix and api_name.startswith(prefix) else api_name
    name = re.sub(rf"^{SET_NUMBER}_", "", name)
    name = re.sub(rf"{SET_NUMBER}(?=_|$)", "", name)
    suffix = ""
    version = re.search(r"_(AD|AP)$", name)
    if version:
        suffix = f" ({version.group(1)})"
        name = name[: version.start()]
    name = name.replace("_", " ").strip()
    return (name or api_name) + suffix


def en_us_champions(en_us):
    """The set's champions as cdragon publishes them, keyed by apiName.

    This is the good source when it exists: the ability description with its
    variables already named and split per star level, plus stats in the units a
    tooltip uses (range in hexes). A set still in development has only PVE
    monsters here, hence the merge in extract_champions.
    """
    entry = next(
        (s for s in en_us.get("setData", []) if s.get("mutator") == set_key()), None
    )
    published = {}
    for champ in (entry or {}).get("champions", []):
        api_name = champ.get("apiName")
        if not api_name:
            continue
        ability = champ.get("ability") or {}
        stats = champ.get("stats") or {}
        published[api_name] = {
            "name": champ.get("name"),
            "cost": champ.get("cost"),
            "role": champ.get("role"),
            "traits": champ.get("traits") or [],
            "stats": {
                "hp": stats.get("hp"),
                "ad": stats.get("damage"),
                "attackSpeed": stats.get("attackSpeed"),
                "armor": stats.get("armor"),
                "mr": stats.get("magicResist"),
                "rangeHexes": stats.get("range"),
                "critChance": stats.get("critChance"),
                "critDamage": stats.get("critMultiplier"),
                "maxMana": stats.get("mana"),
                "startMana": stats.get("initialMana"),
            },
            "ability": {
                "name": ability.get("name"),
                "desc": ability.get("desc"),
                # value[1:4] are the 1/2/3-star entries; the rest are unused.
                "variables": {
                    v.get("name"): (v.get("value") or [])[1:4]
                    for v in ability.get("variables") or []
                    if v.get("name")
                },
            },
        }
    return published


def extract_champions(en_us, map22, strings, hashes):
    """Every unit in the set, merging cdragon's champion list with the bins."""
    prefix = set_prefix(en_us)
    shop = shop_data_by_character(map22)
    published = en_us_champions(en_us)
    champions = []
    seen = set()

    for path in set_character_paths(map22):
        api_name = path.split("/", 1)[-1]
        seen.add(api_name)
        pub = published.get(api_name, {})

        bin_path = os.path.join(
            cache_dir(), "characters", f"{api_name.lower()}.cdtb.bin.json"
        )
        record, spell = None, None
        if os.path.exists(bin_path):
            with open(bin_path, encoding="utf-8") as handle:
                char_bin = json.load(handle)
            record = next(
                (
                    v
                    for v in char_bin.values()
                    if isinstance(v, dict) and v.get("__type") == "TFTCharacterRecord"
                ),
                None,
            )
            spell = extract_spell(char_bin, api_name, strings, hashes)
        record = record or {}

        shop_entry = shop.get(api_name, {})
        # The character lists also carry UI scaffolding -- bench slots, board
        # slots, the augment placeholder. They're TFTCharacterRecords like any
        # other, but nothing you can field: no shop entry, no tier, no ability.
        if not (pub or shop_entry.get("BaseCost") or record.get("tier") or spell):
            continue

        mana = resolve_dict(record.get("primaryAbilityResource"), KNOWN_HASHES, hashes)
        from_strings = lookup_string(strings, shop_entry.get("mDisplayNameTra")) or ""
        pub_stats = pub.get("stats") or {}

        def pick(key, fallback):
            # cdragon's value wins when it has one; the bin fills the gaps.
            value = pub_stats.get(key)
            return fallback if value is None else value

        champions.append(
            {
                "apiName": api_name,
                "name": (
                    pub.get("name")
                    or (from_strings if not from_strings.startswith("<not published") else "")
                    or display_name(api_name, prefix)
                ),
                "cost": pub.get("cost") or shop_entry.get("BaseCost"),
                "tier": record.get("tier"),
                "role": pub.get("role"),
                "traits": pub.get("traits")
                or [
                    t.get("TraitData", "").rsplit("/", 1)[-1]
                    for t in record.get("mLinkedTraits", [])
                ],
                "stats": {
                    "hp": pick("hp", _stat(record, "baseHPModifiable")),
                    "ad": pick("ad", _stat(record, "baseDamageModifiable")),
                    "attackSpeed": pick(
                        "attackSpeed", _stat(record, "attackSpeedModifiable")
                    ),
                    "armor": pick("armor", _stat(record, "baseArmorModifiable")),
                    "mr": pick("mr", _stat(record, "baseMR")),
                    "critChance": pick("critChance", record.get("baseCritChance")),
                    "critDamage": pick("critDamage", record.get("critDamageMultiplier")),
                    "maxMana": pick("maxMana", _stat(mana, "maxMana")),
                    "startMana": pub_stats.get("startMana"),
                    "manaPerAttack": record.get("mManaPerAttack"),
                    # Two different units: cdragon reports hexes, the bin
                    # reports world units (890 = 4 hexes). Kept apart rather
                    # than converted, since the mapping isn't linear.
                    "rangeHexes": pub_stats.get("rangeHexes"),
                    "rangeUnits": _stat(record, "attackRangeModifiable"),
                },
                "ability": pub.get("ability"),
                "spell": spell,
            }
        )

    # A published set can list a champion cdragon knows about but the set's
    # character lists don't reach; don't silently drop it.
    for api_name, pub in published.items():
        if api_name not in seen:
            champions.append(
                {
                    "apiName": api_name,
                    "name": pub.get("name") or display_name(api_name, prefix),
                    "cost": pub.get("cost"),
                    "tier": None,
                    "role": pub.get("role"),
                    "traits": pub.get("traits"),
                    "stats": pub.get("stats"),
                    "ability": pub.get("ability"),
                    "spell": None,
                }
            )

    champions.sort(key=lambda c: (c.get("cost") or 99, c["name"]))
    return champions


def extract_items(en_us):
    """The set's own items/augments/wisps, plus the shared TFT_ item pool."""
    prefix = set_prefix(en_us)
    items = []
    for item in en_us.get("items", []):
        api_name = item.get("apiName") or ""
        if not api_name.startswith((prefix, "TFT_")):
            continue
        desc = item.get("desc") or ""
        items.append(
            {
                "apiName": api_name,
                "name": item.get("name"),
                "desc": desc,
                "effects": resolve_dict(item.get("effects"), desc_hash_table(desc)),
                "associatedTraits": item.get("associatedTraits") or [],
                "composition": item.get("composition") or [],
                "unique": item.get("unique"),
            }
        )
    items.sort(key=lambda i: i["apiName"])
    return items


def build():
    en_us = load_json("en_us.json")
    map22 = load_json("map22.bin.json")
    strings = load_json("tft.stringtable.json").get("entries", {})
    hashes = load_hash_table()

    return {
        "set": SET_NUMBER,
        "setKey": set_key(),
        "channel": CHANNEL,
        "stringTableVersion": load_json("tft.stringtable.json").get("version"),
        "traits": extract_traits(en_us),
        "champions": extract_champions(en_us, map22, strings, hashes),
        "items": extract_items(en_us),
    }


# --------------------------------------------------------------- rendering


def fmt(value):
    """Trim float noise: 0.550000011920929 is 0.55 that survived a float32."""
    if isinstance(value, float):
        rounded = round(value, 4)
        return f"{rounded:g}"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(v) for v in value) + "]"
    return str(value)


def render_traits(data):
    lines = [
        f"# Set {data['set']} traits",
        "",
        f"Generated by `tft_data.py` from CommunityDragon {data['channel']}. Do not edit by hand.",
        "",
    ]
    for trait in data["traits"]:
        lines += [f"## {trait['name']}  `{trait['apiName']}`", ""]
        # The raw description keeps its @Tokens@ -- they name the variables in
        # the table below, so substituting them would lose the mapping.
        for chunk in re.split(r"<br>+", trait["desc"] or ""):
            chunk = re.sub(r"</?row>", "", chunk).strip()
            if chunk:
                lines.append(f"> {chunk}")
        lines.append("")
        if any(bp["variables"] for bp in trait["breakpoints"]):
            names = []
            for bp in trait["breakpoints"]:
                for key in bp["variables"]:
                    if key not in names:
                        names.append(key)
            lines.append("| units | " + " | ".join(names) + " |")
            lines.append("|---" * (len(names) + 1) + "|")
            for bp in trait["breakpoints"]:
                units = str(bp["minUnits"])
                if bp["maxUnits"] and bp["maxUnits"] != bp["minUnits"]:
                    units += f"-{bp['maxUnits']}"
                elif not bp["maxUnits"]:
                    units += "+"
                row = [fmt(bp["variables"].get(n, "")) for n in names]
                lines.append(f"| {units} | " + " | ".join(row) + " |")
        else:
            breaks = ", ".join(str(bp["minUnits"]) for bp in trait["breakpoints"])
            lines.append(f"Breakpoints: {breaks} (no numeric variables)")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_champions(data):
    lines = [
        f"# Set {data['set']} champions",
        "",
        f"Generated by `tft_data.py` from CommunityDragon {data['channel']}. Do not edit by hand.",
        "",
        "Stats are the 1-star base values, exactly as the sim's `Champion.__init__`",
        "wants them. Range is in hexes where cdragon publishes it, otherwise in the",
        "bin's world units (marked `u`; 890u is 4 hexes).",
        "",
        "| champion | api name | cost | hp | ad | as | armor | mr | mana | range | traits |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for champ in data["champions"]:
        stats = champ["stats"] or {}
        if stats.get("rangeHexes") is not None:
            rng = fmt(stats["rangeHexes"])
        elif stats.get("rangeUnits") is not None:
            rng = fmt(stats["rangeUnits"]) + "u"
        else:
            rng = ""
        lines.append(
            "| {name} | `{api}` | {cost} | {hp} | {ad} | {asp} | {armor} | {mr} | {mana} | {rng} | {traits} |".format(
                name=champ["name"],
                api=champ["apiName"],
                cost=fmt(champ.get("cost") or ""),
                hp=fmt(stats.get("hp") or ""),
                ad=fmt(stats.get("ad") or ""),
                asp=fmt(stats.get("attackSpeed") or ""),
                armor=fmt(stats.get("armor") or ""),
                mr=fmt(stats.get("mr") or ""),
                mana=fmt(stats.get("maxMana") or ""),
                rng=rng,
                traits=", ".join(champ["traits"] or []),
            )
        )
    lines.append("")

    for champ in data["champions"]:
        lines += [f"## {champ['name']}  `{champ['apiName']}`", ""]
        ability = champ.get("ability") or {}
        spell = champ.get("spell") or {}

        # cdragon's ability block first when it exists -- description with the
        # variables named, which is what you actually implement from.
        if ability.get("name"):
            lines += [f"**{ability['name']}**", ""]
        if ability.get("desc"):
            text = re.sub(r"<br>+", "\n> ", ability["desc"]).strip()
            lines += [f"> {text}", ""]
        if not (ability or spell):
            lines += ["No ability data for this unit.", ""]
            continue
        if not ability and spell.get("name"):
            lines += [f"**{spell['name']}**", ""]
        if not ability and spell.get("text"):
            lines += [f"> {spell['text']}", ""]

        variables = ability.get("variables") or {}
        for name, values in variables.items():
            lines.append(f"- `{name}`: {fmt(values)}")

        if spell.get("castTime") is not None:
            lines.append(f"- cast time: `{fmt(spell['castTime'])}`")
        if spell.get("dataValuesArePlaceholder"):
            lines.append(
                "- **data values are still the bin template's placeholders** "
                "(`DataValue`/`OtherValue`), i.e. this spell has not been "
                "authored yet -- do not implement from these"
            )
        # The bin's data values are the same numbers cdragon publishes, so
        # they're only worth printing when cdragon hasn't got the set yet.
        if not variables:
            for name, values in (spell.get("dataValues") or {}).items():
                # values[1:4] are the 1/2/3-star entries; the rest are unused.
                lines.append(f"- `{name}`: {fmt(values[1:4] if values else values)}")
        for name, parts in (spell.get("calculations") or {}).items():
            rendered = " + ".join(
                f"{fmt(p['ratio'])} x {p['dataValue']}"
                + (f" ({p['scalesWith']})" if p["scalesWith"] else "")
                for p in parts
            )
            lines.append(f"- `{name}` = {rendered}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_items(data):
    lines = [
        f"# Set {data['set']} items, augments and wisps",
        "",
        f"Generated by `tft_data.py` from CommunityDragon {data['channel']}. Do not edit by hand.",
        "",
    ]
    for item in data["items"]:
        lines.append(f"### {item['name']}  `{item['apiName']}`")
        desc = re.sub(r"<br>+", " ", item["desc"] or "").strip()
        if desc:
            lines.append(f"> {desc}")
        if item["effects"]:
            pairs = ", ".join(f"`{k}` = {fmt(v)}" for k, v in item["effects"].items())
            lines.append(f"- {pairs}")
        lines.append("")
    return "\n".join(lines) + "\n"


README = """# Set {set} reference data

Generated by `../tft_data.py`. **Do not edit these by hand** -- rerun
`python tft_data.py update` and commit the result.

- `traits.md` -- every trait, its description, and its per-breakpoint values
- `champions.md` -- base stats and ability data for every unit in the set
- `items.md` -- items, augments and wisps
- `tft_data.json` -- the same content, normalized, for diffing and scripts

Source: CommunityDragon `{channel}`, string table version `{version}`.

## Reading this

Trait and ability descriptions keep their raw `@Token@` markers on purpose: each
token names the value listed underneath it, so `@ADAPGain*100@%` tells you the
tooltip's percentage is `ADAPGain` x 100, and an ability's `@TotalDamage@` is
whichever formula is spelled out in its `TotalDamage = ...` line.

Ability variables are listed per star level, `[1-star, 2-star, 3-star]` -- the
same order `create_ability_scaling` takes.

A value shown as `{{hash}}` is one whose name no dictionary knows and whose
description doesn't mention it. The number is still correct.

Two markers mean Riot hasn't shipped the data yet, not that the scraper failed:

- `<not published: SomeKey>` -- the string table has no entry for that key
- a spell flagged as using the bin template's placeholder data values

Both are normal for a set still in development, and both go away on their own as
patches land. Don't implement a champion off placeholder data values.
"""


def write_output(data):
    os.makedirs(OUT_DIR, exist_ok=True)
    files = {
        "tft_data.json": json.dumps(data, indent=1, sort_keys=True) + "\n",
        "traits.md": render_traits(data),
        "champions.md": render_champions(data),
        "items.md": render_items(data),
        "README.md": README.format(
            set=data["set"], channel=data["channel"], version=data.get("stringTableVersion")
        ),
    }
    for name, text in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    print(f"Wrote {len(files)} files to {os.path.relpath(OUT_DIR, HERE)}/")


# ------------------------------------------------------------------- diff


def flatten(node, prefix=""):
    """Walk to leaves, keying lists of records by their name rather than index.

    Indexing by position would report every entry as changed the moment Riot
    inserts a champion, which is exactly the patch where you want a readable
    diff.
    """
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            label = index
            if isinstance(value, dict):
                label = value.get("apiName") or value.get("name") or value.get("minUnits") or index
            out.update(flatten(value, f"{prefix}[{label}]"))
    else:
        out[prefix] = node
    return out


def diff(old, new):
    before, after = flatten(old), flatten(new)
    added = [k for k in after if k not in before]
    removed = [k for k in before if k not in after]
    changed = [
        (k, before[k], after[k])
        for k in after
        if k in before and before[k] != after[k]
    ]
    return added, removed, changed


def report_diff(old, new):
    added, removed, changed = diff(old, new)
    if not (added or removed or changed):
        print("No changes since the last run.")
        return False

    after = flatten(new)
    if changed:
        print(f"\n{len(changed)} value(s) changed:")
        for key, was, now in changed:
            print(f"  {key}\n      {fmt(was)}  ->  {fmt(now)}")
    if added:
        print(f"\n{len(added)} added:")
        for key in added[:40]:
            print(f"  {key} = {fmt(after[key])}")
        if len(added) > 40:
            print(f"  ... and {len(added)-40} more")
    if removed:
        print(f"\n{len(removed)} removed:")
        for key in removed[:40]:
            print(f"  {key}")
        if len(removed) > 40:
            print(f"  ... and {len(removed)-40} more")
    return True


def load_previous():
    path = os.path.join(OUT_DIR, "tft_data.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# -------------------------------------------------------------------- cli


def main(argv=None):
    global SET_NUMBER, CHANNEL, OUT_DIR

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", choices=["update", "build", "fetch", "diff"], nargs="?", default="update"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="re-download instead of using .tft_cache/"
    )
    parser.add_argument(
        "--set", type=int, default=SET_NUMBER, help="set number (default %(default)s)"
    )
    parser.add_argument(
        "--channel", default=CHANNEL, help="cdragon channel: pbe, latest, or a patch"
    )
    parser.add_argument("--out", help="write somewhere other than reference/")
    args = parser.parse_args(argv)

    SET_NUMBER = args.set
    CHANNEL = args.channel
    if args.out:
        OUT_DIR = os.path.abspath(args.out)
    elif (SET_NUMBER, CHANNEL) != (18, "pbe"):
        # Cross-checking another set must not overwrite this folder's own
        # reference data; make the caller name a destination.
        sys.exit("--set/--channel other than 18/pbe needs an explicit --out.")

    # diff has to honour --refresh too. It used to accept the flag and ignore
    # it, so `diff --refresh` re-read the cache and reported "No changes"
    # about a download it never made -- a confident answer to a question it
    # had not asked, which is the one failure mode this tool must not have.
    if args.command in ("update", "fetch", "diff"):
        fetch_all(refresh=args.refresh or args.command == "fetch")
    if args.command == "fetch":
        return 0

    data = build()
    print(
        f"Parsed {len(data['traits'])} traits, {len(data['champions'])} champions, "
        f"{len(data['items'])} items."
    )
    print(f"Source: cdragon {CHANNEL}, cache {cache_age()}.")

    previous = load_previous()
    if previous is None:
        print("No previous reference/tft_data.json -- nothing to compare against.")
    else:
        report_diff(previous, data)

    if args.command == "diff":
        print("\n(diff only -- nothing written)")
        return 0

    write_output(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
