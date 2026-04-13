# -*- coding: utf-8 -*-
"""Emit compact {"notes":[...]} JSON for TRVS-Lab import. ASCII-only source."""
import json

WORDS = """gateway
fudge
bolted
autoclave
pipettes
shin
swabs
welt
smack
readily
sterile
metric
sturdy
doornail
negligible
skewing
centrifuge
accelerometer
spool
latch
pendulum
centripetal
instructive
asteroid
planetary
grad
lowball
Guinness
mule
mercury
exponential
progression
sheaf
cripes
doomsday
tangled
crew
animation
jag
goop
scheme
hints
bespoke
devoid
wee
commode
proactive
wander
hustle
peeled
affiliate
terminals
heck
unmanned
dillydally
onboard
microns
been
microscope
deforming
understatement
within
microbes
extraterrestrial
angular
hatch
delicate
wary
plasma
flash
elated
mantel
apocalypse
formaldehyde
speculate
grace
mobile
rep
chuck
huff
preen
retreating
valise
mom
academia
berate
catalyst
credential
Dutch
consistent
speculative
Saskatchewan
accommodate""".strip().splitlines()

# American IPA, primary stress marked with U+02C8
PRON = [
    "/\u02C8\u0261e\u026Atwe\u026A/",
    "/f\u028Cd\u0292/",
    "/\u02C8bo\u028Alt\u026Ad/",
    "/\u02C8\u0254\u02D0to\u028Akle\u026Av/",
    "/p\u026A\u02C8p\u025Bts/",
    "/\u0283\u026An/",
    "/sw\u0251bz/",
    "/w\u025Blt/",
    "/sm\u00E6k/",
    "/\u02C8r\u025Bd\u025Ali/",
    "/\u02C8st\u025Br\u0259l/",
    "/\u02C8m\u025Btr\u026Ak/",
    "/\u02C8st\u025Brdi/",
    "/\u02C8d\u0254\u02D0rne\u026Al/",
    "/\u02C8n\u025B\u0261l\u026Ad\u0292\u0259b\u0259l/",
    "/\u02C8skju\u02D0\u026A\u014B/",
    "/\u02C8s\u025Bntr\u0259fjud\u0292/",
    "/\u00E6ks\u025Bl\u0259\u02C8r\u0251m\u0259t\u0259r/",
    "/spu\u02D0l/",
    "/l\u00E6t\u0283/",
    "/\u02C8p\u025Bnd\u0292\u0259l\u0259m/",
    "/s\u025Bn\u02C8tr\u026Ap\u026At\u0259l/",
    "/\u026An\u02C8str\u028Akt\u026Av/",
    "/\u02C8\u00E6st\u0259r\u0254\u026Ad/",
    "/\u02C8pl\u00E6n\u0259t\u025Bri/",
    "/\u0261r\u00E6d/",
    "/\u02C8lo\u028Ab\u0254\u02D0l/",
    "/\u02C8\u0261\u026An\u026As/",
    "/mju\u02D0l/",
    "/\u02C8m\u025Brkj\u0259ri/",
    "/\u025Bksp\u0259\u02C8n\u025Bn\u0283\u0259l/",
    "/pr\u0259\u02C8\u0261r\u025B\u0283\u0259n/",
    "/\u0283i\u02D0f/",
    "/kra\u026Aps/",
    "/\u02C8du\u02D0mzde\u026A/",
    "/\u02C8t\u00E6\u014B\u0261\u0259ld/",
    "/kru\u02D0/",
    "/\u02C8\u00E6n\u0259me\u026A\u0283\u0259n/",
    "/d\u0292\u00E6\u0261/",
    "/\u0261u\u02D0p/",
    "/ski\u02D0m/",
    "/h\u026Ants/",
    "/b\u026A\u02C8spo\u028Ak/",
    "/d\u026A\u02C8v\u0254\u02D0d/",
    "/wi\u02D0/",
    "/k\u0259\u02C8mo\u028Ad/",
    "/pro\u028A\u02C8\u00E6kt\u026Av/",
    "/\u02C8w\u0251nd\u0259r/",
    "/\u02C8h\u028Cs\u0259l/",
    "/pi\u02D0ld/",
    "/\u0259\u02C8f\u026Alie\u026At/",
    "/\u02C8t\u025Brm\u0259n\u0259lz/",
    "/h\u025Bk/",
    "/\u028Cn\u02C8m\u00E6nd/",
    "/\u02C8d\u026Ali\u02D0d\u00E6li/",
    "/\u02C8\u0251nb\u0254\u02D0rd/",
    "/\u02C8ma\u026Akr\u0251nz/",
    "/b\u026An/",
    "/\u02C8ma\u026Akr\u0259sko\u028Ap/",
    "/d\u026A\u02C8f\u0254\u02D0rm\u026A\u014B/",
    "/\u028Cnd\u0259r\u02C8ste\u026Atm\u0259nt/",
    "/w\u026A\u02C8\u00F0\u026An/",
    "/\u02C8ma\u026Akro\u028Abz/",
    "/\u025Bkstr\u0259t\u0259\u02C8r\u025Bstri\u0259l/",
    "/\u02C8\u00E6\u014B\u0261j\u0259l\u0259r/",
    "/h\u00E6t\u0283/",
    "/\u02C8d\u025Bl\u026Ak\u0259t/",
    "/\u02C8w\u025Bri/",
    "/\u02C8pl\u00E6zm\u0259/",
    "/fl\u00E6\u0283/",
    "/\u026A\u02C8le\u026At\u026Ad/",
    "/\u02C8m\u00E6nt\u0259l/",
    "/\u0259\u02C8p\u0251k\u0259l\u026Aps/",
    "/f\u0254\u02D0r\u02C8m\u00E6ld\u026Aha\u026Ad/",
    "/\u02C8sp\u025Bkj\u0259le\u026At/",
    "/\u0261re\u026As/",
    "/\u02C8mo\u028Ab\u0259l/",
    "/r\u025Bp/",
    "/t\u0283\u028Ck/",
    "/h\u028Cf/",
    "/pri\u02D0n/",
    "/r\u026A\u02C8tri\u02D0t\u026A\u014B/",
    "/v\u0259\u02C8li\u02D0z/",
    "/m\u0251\u02D0m/",
    "/\u00E6k\u0259\u02C8di\u02D0mi\u0259/",
    "/b\u026A\u02C8re\u026At/",
    "/\u02C8k\u00E6t\u0259l\u026Ast/",
    "/kr\u0259\u02C8d\u025Bn\u0283\u0259l/",
    "/d\u028Ct\u0283/",
    "/k\u0259n\u02C8s\u026Ast\u0259nt/",
    "/\u02C8sp\u025Bkj\u0259l\u0259t\u026Av/",
    "/s\u0259\u02C8sk\u00E6t\u0283\u0259w\u0251n/",
    "/\u0259\u02C8k\u0251m\u0259de\u026At/",
]

MEAN = [
    ["n. \u5165\u53e3\uff1b\u901a\u9053", "n. \u9014\u5f84"],
    ["n. \u8f6f\u7cd6", "v. \u642a\u585e"],
    ["v. \u731b\u51b2", "adj. \u56fa\u5b9a\u7684"],
    ["n. \u9ad8\u538b\u706d\u83cc\u5668"],
    ["n. \u79fb\u6db2\u7ba1\uff08\u590d\u6570\uff09"],
    ["n. \u80eb\u9aa8", "v. \u6500\u722c"],
    ["n. \u68c9\u7b7e\uff08\u590d\u6570\uff09", "v. \u64e6\u62ed"],
    ["n. \u97ad\u75d5\uff1b\u8d34\u8fb9"],
    ["n. \u62cd\u6253\u58f0", "v. \u5e26\u6709\u2026\u6c14\u5473"],
    ["adv. \u8f7b\u6613\u5730\uff1b\u4e50\u610f\u5730"],
    ["adj. \u65e0\u83cc\u7684\uff1b\u8d2b\u7620\u7684"],
    ["adj. \u516c\u5236\u7684", "n. \u6307\u6807"],
    ["adj. \u7ed3\u5b9e\u7684"],
    ["n. \u95e8\u9489"],
    ["adj. \u53ef\u5ffd\u7565\u7684"],
    ["v. \u4f7f\u504f\u659c\uff1b\u6b6a\u66f2"],
    ["n. \u79bb\u5fc3\u673a"],
    ["n. \u52a0\u901f\u5ea6\u8ba1"],
    ["n. \u7ebf\u8f74", "v. \u7f20\u7ed5"],
    ["n. \u63d2\u9500", "v. \u63d2\u4e0a"],
    ["n. \u6446"],
    ["adj. \u5411\u5fc3\u7684"],
    ["adj. \u6709\u6559\u80b2\u610f\u4e49\u7684"],
    ["n. \u5c0f\u884c\u661f"],
    ["adj. \u884c\u661f\u7684"],
    ["n. \u6bd5\u4e1a\u751f\uff1b\u7814\u7a76\u751f"],
    ["v. \u6545\u610f\u62a5\u4f4e\u4ef7", "n. \u4f4e\u4ef7"],
    ["n. \u5409\u5c3c\u65af\uff1b\u5065\u529b\u58eb\u5564\u9152"],
    ["n. \u9aa1\u5b50", "n. \u62d6\u978b"],
    ["n. \u6c34\u94f6", "n. \u6c34\u661f"],
    ["adj. \u6307\u6570\u7684\uff1b\u6025\u5267\u7684"],
    ["n. \u8fdb\u5c55\uff1b\u5e8f\u5217"],
    ["n. \u6346\uff1b\u675f"],
    ["interj. \u54ce\u5440\uff08\u5a49\u66f2\uff09"],
    ["n. \u4e16\u754c\u672b\u65e5"],
    ["adj. \u7f20\u7ed3\u7684"],
    ["n. \u5168\u4f53\u8239\u5458\uff1b\u56e2\u961f"],
    ["n. \u52a8\u753b\uff1b\u751f\u6c14"],
    ["n. \u5c16\u9f7f", "n. \u4e00\u9635"],
    ["n. \u9ecf\u7cca\u7cca\u7684\u4e1c\u897f"],
    ["n. \u65b9\u6848\uff1b\u9634\u8c0b", "v. \u5bc6\u8c0b"],
    ["n. \u6697\u793a\uff08\u590d\u6570\uff09", "v. \u63d0\u793a"],
    ["adj. \u5b9a\u5236\u7684"],
    ["adj. \u7f3a\u4e4f\u7684"],
    ["adj. \u5f88\u5c0f\u7684", "n. \u5c0f\u4fbf\uff08\u53e3\u8bed\uff09"],
    ["n. \u4fbf\u6905", "n. \u4e94\u6597\u67dc"],
    ["adj. \u4e3b\u52a8\u7684"],
    ["v. \u6f2b\u6e38", "n. \u6f2b\u6b65"],
    ["v. \u5306\u5fd9\uff1b\u515c\u552e", "n. \u5fd9\u788c"],
    ["adj. \u5265\u4e86\u76ae\u7684", "v. \u5265\u843d"],
    ["v. \u4f7f\u96b6\u5c5e", "n. \u5206\u652f\u673a\u6784"],
    ["n. \u7ec8\u7aef\uff08\u590d\u6570\uff09", "n. \u822a\u7ad9\u697c"],
    ["interj. \u89c1\u9b3c\uff08\u5a49\u66f2\uff09"],
    ["adj. \u65e0\u4eba\u7684"],
    ["v. \u78e8\u8e6d"],
    ["adj. \u5728\u8239\u4e0a/\u673a\u4e0a", "v. \u4f7f\u5165\u804c"],
    ["n. \u5fae\u7c73\uff08\u590d\u6570\uff09"],
    ["v. be \u7684\u8fc7\u53bb\u5206\u8bcd"],
    ["n. \u663e\u5fae\u955c"],
    ["v. \u4f7f\u53d8\u5f62"],
    ["n. \u8f7b\u63cf\u6de1\u5199"],
    ["prep. \u5728\u2026\u4e4b\u5185", "adv. \u5728\u91cc\u9762"],
    ["n. \u5fae\u751f\u7269\uff08\u590d\u6570\uff09"],
    ["adj. \u5730\u7403\u5916\u7684", "n. \u5916\u661f\u4eba"],
    ["adj. \u6709\u89d2\u7684\uff1b\u7626\u524a\u7684"],
    ["v. \u5b75\u5316\uff1b\u5bc6\u8c0b", "n. \u8231\u53e3"],
    ["adj. \u7cbe\u81f4\u7684\uff1b\u8106\u5f31\u7684"],
    ["adj. \u8b66\u60d5\u7684"],
    ["n. \u7b49\u79bb\u5b50\u4f53\uff1b\u8840\u6d46"],
    ["n. \u95ea\u5149", "v. \u95ea\u73b0"],
    ["adj. \u5174\u9ad8\u91c7\u70c8\u7684"],
    ["n. \u58c1\u7089\u67b6"],
    ["n. \u542f\u793a\uff1b\u5927\u707e\u96be"],
    ["n. \u7532\u919b"],
    ["v. \u63a8\u6d4b\uff1b\u6295\u673a"],
    ["n. \u4f18\u96c5\uff1b\u6069\u5178", "v. \u589e\u5149"],
    ["adj. \u53ef\u79fb\u52a8\u7684", "n. \u624b\u673a\uff08\u82f1\uff09"],
    ["n. \u4ee3\u8868\uff1b\u58f0\u8a89"],
    ["v. \u6254", "n. \u5361\u76d8"],
    ["n. \u6012\u6c14", "v. \u55b7\u6c14"],
    ["v. \u6574\u7406\u7fbd\u6bdb\uff1b\u6253\u626e"],
    ["v. \u64a4\u9000\uff1b\u540e\u9000"],
    ["n. \u5c0f\u65c5\u884c\u7bb1"],
    ["n. \u5988\u5988"],
    ["n. \u5b66\u672f\u754c"],
    ["v. \u4e25\u5389\u8bad\u65a5"],
    ["n. \u50ac\u5316\u5242\uff1b\u8bf1\u56e0"],
    ["n. \u8d44\u5386\uff1b\u8bc1\u4e66"],
    ["adj. \u8377\u5170\u7684", "n. \u8377\u5170\u8bed"],
    ["adj. \u4e00\u81f4\u7684"],
    ["adj. \u63a8\u6d4b\u7684\uff1b\u6295\u673a\u7684"],
    ["n. \u8428\u65af\u5580\u5f7b\u6e29\uff08\u7701\uff09"],
    ["v. \u5bb9\u7eb3\uff1b\u9002\u5e94"],
]

EDEF = [
    "An entrance or opening, or a way to reach something.",
    "A soft candy, or to fake or dodge a direct answer.",
    "Ran off suddenly, or fastened with a bolt.",
    "A pressurized chamber that sterilizes with steam.",
    "Small lab tools for moving exact liquid volumes.",
    "The front of the leg below the knee, or to climb awkwardly.",
    "Sticks with absorbent tips for samples or cleaning.",
    "A raised mark on skin, or a sewn strip on fabric.",
    "A slap or sharp sound, or to suggest a quality strongly.",
    "Easily and quickly, or willingly.",
    "Free of living microbes, or unable to reproduce.",
    "Using meters and grams, or a measured statistic.",
    "Strong, solid, and hard to break.",
    "A metal stud on a door; used in “dead as a doornail.”",
    "So small it can be ignored.",
    "Distorting or biasing results away from the true center.",
    "A machine that spins tubes to separate denser materials.",
    "A sensor that measures acceleration.",
    "A reel for thread or wire, or to wind onto one.",
    "A fastening catch, or to secure with one.",
    "A swinging weight that regulates timing.",
    "Directed toward the center of curved motion.",
    "Teaching useful lessons by example or explanation.",
    "A small rocky object orbiting the Sun.",
    "Relating to planets or planet-scale systems.",
    "Informal for graduate or grad student.",
    "To quote or offer an unfairly low price.",
    "Irish stout beer or the Guinness record brand.",
    "A horse–donkey hybrid, or a backless slipper shoe.",
    "The element mercury or the innermost planet.",
    "Involving exponents, or growing by constant multipliers.",
    "A series of advancing steps or stages.",
    "A bundle of stalks or papers.",
    "A mild exclamation like “jeez.”",
    "A final catastrophic day or end-times scenario.",
    "Twisted together in knots.",
    "A team working together, especially on a ship or set.",
    "Moving pictures, or lively energy.",
    "A sharp notch or a short spell of excess.",
    "Informal messy goo or paste.",
    "A plan or plot, sometimes dishonest.",
    "Small clues or indirect suggestions.",
    "Custom-made to order.",
    "Completely lacking something.",
    "Very small, or urine (informal British).",
    "A bedside toilet chair, or a chest of drawers.",
    "Acting early to prevent problems.",
    "To roam, or a slow stroll.",
    "To hurry or push; busy street energy.",
    "With the outer layer removed.",
    "To connect as a branch, or a linked partner.",
    "Endpoints of wires or transport hubs.",
    "A mild substitute for “hell.”",
    "Operated without people aboard.",
    "To waste time hesitating.",
    "On a vehicle, or to train a new hire.",
    "Units of one millionth of a meter.",
    "Past participle of be: existed or visited.",
    "An instrument for seeing tiny objects.",
    "Changing shape under stress or heat.",
    "Saying less than the full truth for effect.",
    "Inside a limit of space, time, or amount.",
    "Tiny organisms like bacteria.",
    "From beyond Earth; space alien (informal).",
    "Having angles; thin and bony-looking.",
    "To emerge from an egg, or a hatch opening.",
    "Fragile, fine, or easily harmed.",
    "Cautious about risk.",
    "Ionized gas, or the liquid part of blood.",
    "A sudden burst of light, or to appear briefly.",
    "Thrilled and very happy.",
    "The shelf above a fireplace.",
    "Massive destruction or end-of-world imagery.",
    "A strong-smelling preservative gas.",
    "To guess without proof, or trade for risky gain.",
    "Elegance, or a prayer before eating.",
    "Movable, or a cellphone (UK).",
    "Short for representative or reputation.",
    "To throw casually, or a lathe jaw.",
    "Annoyed puffing, or to breathe angrily.",
    "Birds tidy feathers; people primp proudly.",
    "Moving backward or withdrawing.",
    "A small travel case.",
    "Mother (especially US English).",
    "Universities and scholarly institutions.",
    "To scold harshly and at length.",
    "Something that speeds a reaction or sparks change.",
    "Proof of qualification, or login proof.",
    "From the Netherlands or its language.",
    "Matching over time; not self-contradictory.",
    "Based on guesses, or financially risky.",
    "A Canadian prairie province.",
    "To house, adjust for, or make room for.",
]

ROOT = [
    "gate\uff08\u95e8\uff09+ way\uff08\u8def\uff09",
    "-",
    "bolt\uff08\u87ba\u6813/\u8dd1\uff09+ -ed",
    "auto-\uff08\u81ea\u52a8\uff09+ clave\uff08\u952e/\u58f3\uff09",
    "pipette + -s",
    "-",
    "swab + -s",
    "-",
    "-",
    "ready + -ly",
    "steril- + -e",
    "metr-\uff08\u6d4b\u91cf\uff09+ -ic",
    "-",
    "door + nail",
    "neg-\uff08\u5426\u5b9a\uff09+ lig-\uff08\u8f7b\uff09+ -ible",
    "skew + -ing",
    "centr-\uff08\u4e2d\u5fc3\uff09+ fug-\uff08\u9003\uff09",
    "accelerate + -ometer",
    "-",
    "-",
    "pend-\uff08\u60ac\u6302\uff09+ -ulum",
    "centri-\uff08\u4e2d\u5fc3\uff09+ pet-\uff08\u8d8b\u5411\uff09+ -al",
    "instruct + -ive",
    "aster-\uff08\u661f\uff09+ -oid",
    "planet + -ary",
    "abbrev. graduate",
    "low + ball",
    "\u4e13\u6709\u540d\u8bcd",
    "-",
    "Mercury\uff08\u795e/\u5143\u7d20\uff09",
    "ex-\uff08\u51fa\uff09+ pon-\uff08\u653e\u7f6e\uff09+ -ential",
    "progress + -ion",
    "-",
    "\u5a49\u66f2\u8bed",
    "doom + day",
    "tangle + -ed",
    "-",
    "animate + -ion",
    "-",
    "-",
    "-",
    "hint + -s",
    "be- + spoke",
    "de- + void\uff08\u7a7a\uff09",
    "-",
    "\u6cd5\u8bed commode",
    "pro- + active",
    "-",
    "-",
    "peel + -ed",
    "ad- + fili-\uff08\u7ed3\u76df\uff09",
    "terminal + -s",
    "\u5a49\u66f2\u8bed",
    "un- + manned",
    "dally \u91cd\u53e0",
    "on + board",
    "micro- + micron + -s",
    "be + -en",
    "micro- + scope",
    "de- + form + -ing",
    "under + statement",
    "with- + in",
    "micro- + -be + -s",
    "extra- + terrestrial",
    "angle + -ar",
    "-",
    "delic- + -ate",
    "-",
    "-",
    "-",
    "e- + lat- + -ed",
    "\u53d8\u4f53 mantle",
    "apo- + calypse",
    "form- + aldehyde",
    "spec- + -ulate",
    "-",
    "-",
    "abbrev.",
    "-",
    "-",
    "-",
    "re- + treat + -ing",
    "\u6cd5\u8bed valise",
    "mama",
    "academy + -ia",
    "be- + rate\uff08\u65a5\u8d23\uff09",
    "cata- + lyst",
    "cred-\uff08\u4fe1\uff09+ -ential",
    "-",
    "con- + sist + -ent",
    "speculate + -ive",
    "\u5730\u540d",
    "ac- + commod-\uff08\u65b9\u4fbf\uff09+ -ate",
]

EX = [
    "The city\u2019s north gateway was crowded with tourists.",
    "Grandma makes chocolate fudge every Christmas.",
    "He bolted from the room when the alarm sounded.",
    "Lab glassware goes into the autoclave before reuse.",
    "She labeled a rack of clean pipettes.",
    "He scraped his shin on the coffee table.",
    "Nurses took nasal swabs for testing.",
    "A red welt rose where the branch had struck.",
    "The book smacks of old-fashioned snobbery.",
    "She readily admitted her mistake.",
    "Surgeons work in a sterile field.",
    "Canada uses metric units for distance.",
    "They built a sturdy bench for the porch.",
    "In stories, he was as dead as a doornail.",
    "The error was negligible for our purposes.",
    "Outliers were skewing the average upward.",
    "Blood tubes spin in the centrifuge for five minutes.",
    "Phones use an accelerometer to detect orientation.",
    "Film unwound from a metal spool.",
    "The gate latch clicked shut behind her.",
    "The clock\u2019s pendulum swung steadily.",
    "Centripetal force keeps the car on the curved road.",
    "The documentary was instructive for beginners.",
    "An asteroid passed relatively close to Earth.",
    "They discussed planetary science missions.",
    "She\u2019s a first-year law grad student.",
    "The buyer tried to lowball us on the car.",
    "He ordered a pint of Guinness at the pub.",
    "The pack mule carried supplies up the trail.",
    "Old thermometers contained mercury.",
    "Social posts can drive exponential growth in views.",
    "The disease follows a slow progression.",
    "He laid a sheaf of wheat by the barn door.",
    "Cripes, I almost missed the train!",
    "Preppers stock supplies for a doomsday scenario.",
    "Her headphones came out of the bag tangled.",
    "The flight crew welcomed passengers on board.",
    "The studio released a new animation feature.",
    "He went on a crying jag after the breakup.",
    "Wipe that goop off your hands before dinner.",
    "They uncovered an insurance fraud scheme.",
    "She dropped hints about her birthday gift.",
    "He ordered a bespoke suit from a London tailor.",
    "The landscape was devoid of trees.",
    "The kitten gave a wee meow.",
    "The antique commode stood beside the bed.",
    "A proactive manager fixes issues before they escalate.",
    "We wandered through the old quarter at dusk.",
    "Street vendors hustle souvenirs to tourists.",
    "She ate a peeled orange on the train.",
    "The clinic is affiliated with a major hospital.",
    "Flight information flickered on the departure terminals.",
    "What the heck is going on?",
    "Unmanned drones surveyed the coastline.",
    "Stop dillydallying and get dressed.",
    "We onboard new hires during their first week.",
    "Filters trap particles only a few microns wide.",
    "I have been to Paris twice.",
    "Bacteria are visible under a microscope.",
    "Heat was deforming the plastic panel.",
    "Calling the storm \u201cannoying\u201d was a huge understatement.",
    "Reply within three business days.",
    "Soil teems with helpful microbes.",
    "They searched for signs of extraterrestrial life.",
    "The room\u2019s angular furniture looked modern.",
    "Chicks hatch after about three weeks.",
    "Handle the delicate glassware with care.",
    "Cats are wary of strangers.",
    "The sun is mostly hot plasma.",
    "Lightning flashed across the sky.",
    "She was elated when she got the offer.",
    "Stockings hung from the mantel.",
    "The film imagines a zombie apocalypse.",
    "Some labs store specimens in formaldehyde.",
    "Analysts speculate that rates will fall next year.",
    "She accepted the criticism with quiet grace.",
    "Children are more mobile after they learn to walk.",
    "He\u2019s the sales rep for our region.",
    "Chuck the ball over here!",
    "She left in a huff after the argument.",
    "Swans preen on the riverbank.",
    "The glacier is slowly retreating.",
    "He packed a valise for the weekend trip.",
    "Mom drove us to school.",
    "She chose a career in academia.",
    "The coach berated the team for lazy defense.",
    "Her speech was a catalyst for reform.",
    "The job requires teaching credentials.",
    "She speaks Dutch fluently.",
    "His story was consistent with the evidence.",
    "The article was highly speculative.",
    "Wheat fields stretch across Saskatchewan.",
    "The hall can accommodate two hundred guests.",
]

COLL = [
    ["gateway drug", "gateway to success", "network gateway"],
    ["fudge the numbers", "hot fudge", "fudge sauce"],
    ["bolted the door", "bolted upright", "bolted down food"],
    ["autoclave cycle", "steam autoclave", "autoclave tape"],
    ["micropipettes", "disposable pipettes", "pipette tips"],
    ["shin guard", "bang your shin", "shin splints"],
    ["cotton swabs", "nasal swabs", "swab the deck"],
    ["shoe welt", "raise a welt", "welt on the skin"],
    ["smack in the face", "smack of hypocrisy", "smack dab"],
    ["readily available", "readily apparent", "readily accept"],
    ["sterile field", "sterile technique", "sterile environment"],
    ["metric system", "metric ton", "key metric"],
    ["sturdy frame", "sturdy boots", "sturdy construction"],
    ["dead as a doornail", "hammered doornail"],
    ["negligible risk", "negligible amount", "negligible difference"],
    ["skewing the data", "skewing results", "skewing the average"],
    ["centrifuge tube", "benchtop centrifuge", "centrifuge speed"],
    ["MEMS accelerometer", "tri-axis accelerometer"],
    ["thread spool", "spool of wire", "spool up"],
    ["door latch", "latch onto", "safety latch"],
    ["pendulum swing", "Foucault pendulum", "swing of the pendulum"],
    ["centripetal force", "centripetal acceleration"],
    ["instructive example", "instructive lesson"],
    ["asteroid belt", "near-Earth asteroid"],
    ["planetary system", "planetary orbit", "planetary gear"],
    ["high school grad", "grad school", "new grad"],
    ["lowball offer", "lowball estimate"],
    ["Guinness World Records", "pint of Guinness"],
    ["stubborn as a mule", "drug mule", "mule slippers"],
    ["mercury poisoning", "planet Mercury", "mercury vapor"],
    ["exponential growth", "exponential function", "exponential increase"],
    ["arithmetic progression", "career progression", "natural progression"],
    ["a sheaf of papers", "sheaf of wheat", "sheaf of arrows"],
    ["Oh cripes", "for cripes' sake"],
    ["doomsday clock", "doomsday scenario", "doomsday prepper"],
    ["tangled hair", "tangled web", "tangled up"],
    ["film crew", "crew members", "flight crew"],
    ["computer animation", "stop-motion animation", "with animation"],
    ["on a jag", "crying jag"],
    ["sticky goop", "beauty goop"],
    ["pension scheme", "color scheme", "scheme to cheat"],
    ["drop hints", "subtle hints", "helpful hints"],
    ["bespoke tailoring", "bespoke software", "bespoke furniture"],
    ["devoid of evidence", "devoid of humor"],
    ["wee bit", "wee hours", "wee child"],
    ["bedside commode", "antique commode"],
    ["proactive approach", "proactive measures"],
    ["wander off", "wander around", "mind wanders"],
    ["hustle and bustle", "side hustle", "hustle hard"],
    ["eyes peeled", "peeled potatoes", "peeled orange"],
    ["affiliate program", "affiliate marketing", "affiliate member"],
    ["airport terminals", "computer terminals", "battery terminals"],
    ["for heck's sake", "oh heck", "what the heck"],
    ["unmanned aerial vehicle", "unmanned spacecraft"],
    ["dillydally around", "no time to dillydally"],
    ["onboard training", "welcome onboard", "get onboard"],
    ["particles in microns", "microns thick", "micron filter"],
    ["has been", "have been there", "been around"],
    ["electron microscope", "light microscope", "under the microscope"],
    ["deforming stress", "deforming metal"],
    ["British understatement", "master of understatement"],
    ["within reach", "within limits", "from within"],
    ["gut microbes", "harmful microbes", "soil microbes"],
    ["extraterrestrial life", "extraterrestrial intelligence"],
    ["angular momentum", "angular velocity", "angular face"],
    ["hatch a plan", "escape hatch", "hatch eggs"],
    ["delicate balance", "delicate skin", "delicate situation"],
    ["wary of strangers", "keep a wary eye", "wary approach"],
    ["blood plasma", "plasma membrane", "plasma TV"],
    ["in a flash", "news flash", "camera flash"],
    ["feel elated", "elated mood"],
    ["mantel clock", "fireplace mantel"],
    ["post-apocalypse", "zombie apocalypse"],
    ["formaldehyde solution", "formaldehyde exposure"],
    ["speculate about", "speculate on stocks"],
    ["say grace", "fall from grace", "social graces"],
    ["mobile phone", "mobile app", "mobile home"],
    ["sales rep", "bad rep", "gym reps"],
    ["chuck out", "chuck steak", "chuck it away"],
    ["in a huff", "huff and puff"],
    ["preen feathers", "preen in the mirror"],
    ["retreating glacier", "retreating army", "retreating tide"],
    ["leather valise", "pack a valise"],
    ["stay-at-home mom", "mom and dad"],
    ["world of academia", "academia and industry"],
    ["berate someone publicly", "berate the team"],
    ["catalyst for change", "enzyme catalyst"],
    ["academic credentials", "login credentials"],
    ["Dutch oven", "go Dutch", "Dutch courage"],
    ["consistent quality", "consistent with"],
    ["speculative fiction", "speculative trading"],
    ["Saskatchewan River", "Province of Saskatchewan"],
    ["accommodate guests", "accommodate requests", "accommodate disabilities"],
]


def main():
    assert len(WORDS) == 93
    assert len(PRON) == 93
    for name, seq in [
        ("MEAN", MEAN),
        ("EDEF", EDEF),
        ("ROOT", ROOT),
        ("EX", EX),
        ("COLL", COLL),
    ]:
        assert len(seq) == 93, (name, len(seq))

    notes = []
    for i, w in enumerate(WORDS):
        pron = PRON[i]
        if not (pron.startswith("/") and pron.endswith("/")):
            raise SystemExit(f"bad pron {w}: {pron!r}")
        m = MEAN[i]
        if not 1 <= len(m) <= 3:
            raise SystemExit(f"meaning len {w}: {m}")
        c = COLL[i]
        if not 2 <= len(c) <= 4:
            raise SystemExit(f"coll len {w}: {c}")
        notes.append(
            {
                "word": w,
                "pronunciation": pron,
                "meaning": m,
                "english_definition": EDEF[i],
                "root": ROOT[i],
                "example": EX[i],
                "collocations": c,
                "audio_html": "",
            }
        )

    print(json.dumps({"notes": notes}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
