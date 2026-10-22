#!/usr/bin/env python3
"""
Bible-lands interactive map generator — reusable module.
- overview map  -> injected into the homepage (OT/NT toggle + legend)
- per-sermon focus maps -> one per sermon/passage page, zoomed to the
  geography relevant to that book / letter (Rome, Ephesus, Galatia, Asia
  Minor, Athens, Jerusalem, Egypt->Sinai...).

Engine is self-contained (no CDN, works on file://): ESRI World Imagery tiles
load on demand; markers/routes/regions are reprojected live in Web Mercator.

Usage (importable):
    from build_map import overview_block, sermon_map_block, detect_book
    open('map-block.html','w').write(overview_block())
Run standalone to regenerate the homepage block.
"""
import os, sys, json, math

HOME = os.path.expanduser("~")
PROJ = os.path.join(HOME, "Desktop/Hermes/Church Site")

TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

# ================================================================= overview
CITIES = [
    # name, era, lat, lon, note, label side
    ("Jerusalem","both",31.778,35.235,"Capital of Judah; site of the Temple; centre of Jesus' ministry, crucifixion and resurrection.","r"),
    ("Jericho","both",31.857,35.444,"First city conquered at the entry into Canaan (Josh 6); scene of Jesus' healing of Bartimaeus (Mark 10).","r"),
    ("Bethlehem","both",31.705,35.203,"Birthplace of David and of Jesus (Micah 5:2; Luke 2).","l"),
    ("Hebron","both",31.532,35.099,"Where Abraham sojourned and David was first anointed king (Gen 13; 2 Sam 2).","l"),
    ("Joppa","both",32.053,34.751,"Port (Jonah sailed from here); where Peter received the vision (Acts 10).","l"),
    ("Tyre","both",33.272,35.212,"Phoenician seaport that supplied timber for the Temple (1 Kgs 5); Jesus visited its region (Mark 7).","l"),
    ("Sidon","both",33.562,35.388,"Ancient Phoenician city; mentioned in the prophets and in Acts 27.","r"),
    ("Damascus","both",33.513,36.292,"Aramaean capital east of Israel; on the road where Paul was converted (Acts 9).","r"),
    ("Mt Sinai","ot",28.539,33.973,"Where Israel received the Law, via Moses (Exodus 19-20).","r"),
    ("Kadesh Barnea","ot",30.653,34.420,"Israel's camp on the edge of the wilderness; the spy mission and rebellion (Num 13-14).","r"),
    ("Gaza","ot",31.506,34.490,"One of the five Philistine cities (Judg 16; Acts 8).","l"),
    ("Beersheba","ot",31.251,34.791,"\"Well of the oath\" — southern limit of the land (Gen 21).","l"),
    ("Lachish","ot",31.565,34.848,"Fortified Judahite city; its letters tell of the Babylonian siege (2 Kgs 18).","l"),
    ("Shiloh","ot",32.057,35.289,"Where the tabernacle and Ark rested in the days of the judges (1 Sam 1-4).","r"),
    ("Bethel","ot",31.930,35.220,"Where Jacob dreamed of the ladder (Gen 28); later a rival sanctuary (1 Kgs 12).","l"),
    ("Shechem","ot",32.214,35.253,"Between mountains Ebal and Gerizim; the covenant renewed (Josh 8, 24).","l"),
    ("Samaria","ot",32.277,35.190,"Capital of the northern kingdom of Israel (1 Kgs 16).","l"),
    ("Rabbah","ot",31.954,35.935,"Capital of the Ammonites — \"Rabbah of the Ammonites\" (2 Sam 11).","r"),
    ("Megiddo","ot",32.584,35.182,"Stronghold over the Jezreel valley; the name became \"Armageddon\" (Rev 16:16).","l"),
    ("Capernaum","nt",32.880,35.575,"Jesus' Galilean base and adopted town (Matt 4:13); synagogue and healings.","r"),
    ("Bethsaida","nt",32.810,35.618,"Home of Peter, Andrew and Philip; feeding of the five thousand nearby (Luke 9).","r"),
    ("Chorazin","nt",32.904,35.561,"Town rebuked by Jesus for unbelief (Matt 11:21).","l"),
    ("Cana","nt",32.747,35.339,"Site of Jesus' first sign — water into wine (John 2).","l"),
    ("Nazareth","nt",32.703,35.297,"Jesus' hometown where he grew up and first preached (Luke 4).","l"),
    ("Nain","nt",32.632,35.349,"Where Jesus raised the widow's son (Luke 7:11-17).","r"),
    ("Sychar","nt",32.211,35.290,"Samaritan town of Jacob's well where Jesus met the woman (John 4).","r"),
    ("Caesarea","nt",32.502,34.903,"Roman port and seat of government; Paul imprisoned here (Acts 23-26).","l"),
    ("Emmaus","nt",31.839,34.988,"Village where the risen Jesus walked with two disciples (Luke 24).","l"),
    ("Bethany","nt",31.771,35.264,"Home of Mary, Martha and Lazarus; the tomb and resurrection of Lazarus (John 11).","r"),
]
EXODUS = [
    [30.62,31.90],[30.38,32.28],[29.95,32.55],[29.60,32.75],[29.70,33.30],
    [28.54,33.97],[29.85,34.05],[30.65,34.42],[30.85,35.30],[31.40,35.75],
    [31.70,35.60],[31.86,35.44],
]
NT_PATH = [
    [32.70,35.30],[32.50,35.28],[32.28,35.19],[32.10,35.30],
    [31.86,35.44],[31.84,35.32],[31.78,35.27],[31.778,35.235],
]
JORDAN = [
    [32.82,35.59],[32.60,35.56],[32.40,35.56],[32.20,35.57],[32.00,35.57],
    [31.80,35.55],[31.60,35.50],[31.50,35.46],
]
REGIONS = [
    ["M E D I T E R R A N E A N  S E A",32.45,32.10,-24,"#8FB8C4"],
    ["Egypt & Goshen",30.75,31.95,0,"#E6C98F"],
    ["Sinai",29.35,33.95,0,"#CDB98F"],
    ["Negev",30.65,34.75,0,"#CDB98F"],
    ["Philistia",31.62,34.55,0,"#E6B7A6"],
    ["Judah",31.40,35.05,0,"#C9B8E6"],
    ["Israel / Samaria",32.18,35.08,0,"#C9B8E6"],
    ["Galilee",32.90,35.33,0,"#A6D9A0"],
    ["Ammon",32.02,35.98,0,"#C9B8E6"],
    ["Moab",31.45,35.90,0,"#C9B8E6"],
    ["Edom",30.55,35.60,0,"#C9B8E6"],
    ["Syria",33.25,36.10,0,"#C9B8E6"],
]
GALILEE = {"lat":32.82,"lon":35.40,"rx":0.17,"ry":0.13}
BOUNDARY = [[[31.99,34.80],[31.86,35.30]]]
WATERS = [[32.805,35.545,0.085,0.075,"Sea of Galilee"],[31.46,35.39,0.38,0.04,"Dead Sea"]]

def _d(init, cities, **kw):
    d = {"cities":cities, "exodus":kw.get("exodus",[]), "nt_path":kw.get("nt_path",[]),
         "jordan":kw.get("jordan",[]), "regions":kw.get("regions",[]),
         "galilee":kw.get("galilee"), "boundary":kw.get("boundary",[]),
         "waters":kw.get("waters",[]), "zones":kw.get("zones",[]),
         "routes":kw.get("routes",[]),
         "route_label":kw.get("route_label","EXODUS ROUTE"),
         "tiles":TILES, "init":init}
    return d

OVERVIEW = _d({"lon":35.35,"lat":31.45,"z":9.2}, CITIES,
              exodus=EXODUS, nt_path=NT_PATH, jordan=JORDAN, regions=REGIONS,
              galilee=GALILEE, boundary=BOUNDARY, waters=WATERS)

# ================================================================= per-book
# Each focus: title, init centre/zoom, cities, optional zones + exodus route.
BOOKS = {
 "romans": dict(title="Romans — the gospel to Rome", init=(41.88,12.48,5.1),
   cities=[("Rome",41.9028,12.4964,"Written to the church in Rome — Paul's great letter on the gospel, then applied to daily love and unity.","r")],
   zones=[dict(lat=41.6,lon=12.6,rx=2.6,ry=1.9,label="ITALIA")]),
 "ephesians": dict(title="Ephesians — to the church in Ephesus", init=(38.1,27.6,6.9),
   cities=[("Ephesus",37.941,27.342,"A leading city of the province of Asia; the letter on grace, and the church as Christ's body and household.","r"),
           ("Smyrna",38.420,27.142,"One of the seven churches of Revelation (Rev 2:8).","l"),
           ("Pergamum",39.122,27.180,"Another of the seven churches (Rev 2:12).","l")],
   zones=[dict(lat=38.4,lon=27.6,rx=1.7,ry=1.4,label="ASIA")]),
 "colossians": dict(title="Colossians — to Colossae in the Lycus valley", init=(37.9,29.3,7.0),
   cities=[("Colossae",37.786,29.266,"Believers in the Lycus valley; the letter on Christ's supreme headship.","r"),
           ("Laodicea",37.834,29.107,"City addressed nearby; believers the letter was to be shared with (Col 4:16).","l"),
           ("Hierapolis",37.928,29.128,"Neighbouring city (Col 4:13).","l")]),
 "galatians": dict(title="Galatians — to the churches of Galatia", init=(38.7,31.6,6.4),
   cities=[("Antioch (Pisidia)",38.306,31.190,"Where Paul first preached on the first journey (Acts 13).","l"),
           ("Iconium",37.873,32.484,"Galatian city visited with Barnabas (Acts 14).","r"),
           ("Lystra",37.581,32.344,"Where Paul was stoned, then returned (Acts 14).","l"),
           ("Derbe",37.348,33.545,"Southernmost Galatian city of the first journey (Acts 14).","r")],
   zones=[dict(lat=39.2,lon=33.2,rx=2.2,ry=1.8,label="GALATIA")]),
 "1 peter": dict(title="1 Peter — to the scattered believers of Asia Minor", init=(39.5,34.0,6.2),
   cities=[("Pontus",40.90,37.00,"One of the provinces Peter addresses (1 Pet 1:1).","r"),
           ("Galatia",39.20,34.20,"(1 Pet 1:1).","l"),
           ("Cappadocia",38.90,35.60,"(1 Pet 1:1).","l"),
           ("Asia",38.50,28.60,"(1 Pet 1:1).","l"),
           ("Bithynia",40.60,32.20,"(1 Pet 1:1).","l"),
           ("'Babylon' (Rome)",41.90,12.50,"The symbolic 'Babylon' Peter writes from (1 Pet 5:13).","r")],
   zones=[dict(lat=40.0,lon=34.5,rx=3.4,ry=2.6,label="ASIA MINOR")]),
 "psalm": dict(title="Psalms — in the city of the great King", init=(31.78,35.20,8.4),
   cities=[("Jerusalem",31.778,35.235,"The psalmist's city — temple worship, repentance and hope.","r"),
           ("Mt Zion",31.768,35.228,"Temple mount and city of David.","l")]),
 "acts": dict(title="Acts — Paul's Mediterranean mission", init=(36.4,25.5,5.3),
   cities=[("Jerusalem",31.778,35.235,"Where the church began (Acts 1-7).","r"),
           ("Antioch (Syria)",36.200,36.160,"The church's sending base for mission (Acts 11, 13).","l"),
           ("Tarsus",36.902,34.898,"Paul's home town (Acts 9:11).","l"),
           ("Athens",37.9715,23.7260,"The Areopagus address (Acts 17).","l"),
           ("Corinth",37.905,22.916,"Eighteen months planting the church (Acts 18).","l"),
           ("Ephesus",37.941,27.342,"Two years of powerful ministry (Acts 19).","l"),
           ("Thessalonica",40.640,22.944,"Riot and a church (Acts 17).","r"),
           ("Philippi",41.012,24.342,"The first European church (Acts 16).","r"),
           ("Rome",41.9028,12.4964,"The end of the road — and the gospel's arrival (Acts 28).","r")],
           zones=[dict(lat=36.5,lon=22.5,rx=5.2,ry=3.6,label="MEDITERRANEAN")],
           routes=[
           dict(label="PAUL'S JOURNEYS", color="#C89B3C", label_pt=[38.9,31.3],
           pts=[[36.20,36.16],[37.56,36.06],[37.87,32.484],[38.306,31.19],[36.96,30.85],
            [39.7,26.5],[40.55,24.5],[41.012,24.342],[40.640,22.944],[37.9715,23.726],
            [37.905,22.916],[38.0,27.34],[37.318,26.51]]),
           dict(label="VOYAGE TO ROME", color="#F2C879", label_pt=[38.5,19.5],
           pts=[[38.0,27.34],[37.318,26.51],[35.2,26.0],[36.5,24.0],[39.5,22.5],
            [36.9,18.0],[40.84,14.25],[41.90,12.50]]),
           ]),
 "nehemiah": dict(title="Nehemiah — rebuilding Jerusalem", init=(31.79,35.24,8.4),
   cities=[("Jerusalem",31.778,35.235,"Rebuilding the walls — the restoration of God's city.","r")]),
 "exodus": dict(title="Exodus — from Egypt to Sinai", init=(30.5,32.6,6.8),
   cities=[("Goshen (Egypt)",30.85,31.75,"Where Israel sojourned; the oppression and the plagues.","l"),
           ("Mt Sinai",28.539,33.973,"Where Israel received the Law (Exodus 19-20).","r"),
           ("Kadesh Barnea",30.653,34.420,"Wilderness camp on the doorstep of the land (Num 13).","r")],
   exodus=EXODUS),
 "hebrews": dict(title="Hebrews — in the shadow of the temple", init=(31.79,35.23,8.3),
   cities=[("Jerusalem",31.778,35.235,"The temple and old covenant; Christ as the greater High Priest.","r"),
           ("Mt Zion / Temple",31.768,35.224,"The priesthood, sacrifice and sanctuary Hebrews unfolds.","l")]),
 "corinthians": dict(title="Corinthians — to the church in Corinth", init=(37.9,22.7,8.0),
   cities=[("Corinth",37.905,22.916,"The great port of Achaia where Paul founded the church (Acts 18).","r"),
           ("Cenchreae",37.885,22.988,"Corinth's eastern harbour (Rom 16:1).","l")]),
 "philippians": dict(title="Philippians — to the church in Philippi", init=(41.02,24.35,8.0),
   cities=[("Philippi",41.012,24.342,"Paul's first European church, planted in a Macedonian city (Acts 16).","r")]),
 "thessalonians": dict(title="Thessalonians — to the church in Thessalonica", init=(40.64,22.95,8.0),
   cities=[("Thessalonica",40.640,22.944,"The young Macedonian church on the Via Egnatia (Acts 17).","r")]),
 "timothy": dict(title="Timothy — letters to the young pastor", init=(38.1,27.5,7.3),
   cities=[("Ephesus",37.941,27.342,"Where Timothy was left to guard sound doctrine (1 Tim 1:3).","r")]),
 "titus": dict(title="Titus — on the island of Crete", init=(35.2,24.9,7.1),
   cities=[("Crete (Gortyna)",35.056,25.029,"Left in Crete to set the churches in order (Titus 1:5).","l")],
   zones=[dict(lat=35.2,lon=24.9,rx=0.9,ry=0.5,label="CRETE")]),
 "philemon": dict(title="Philemon — back to Colossae", init=(37.86,29.3,7.4),
   cities=[("Colossae",37.786,29.266,"Letter about the runaway slave Onesimus, sent home.","r")]),
 "revelation": dict(title="Revelation — Patmos and the seven churches", init=(38.0,27.7,6.7),
   cities=[("Patmos",37.318,26.512,"Where John received the Revelation (Rev 1:9).","l"),
           ("Ephesus",37.941,27.342,"The first of the seven churches (Rev 2:1).","l"),
           ("Smyrna",38.420,27.142,"(Rev 2:8).","l"),
           ("Pergamum",39.122,27.180,"(Rev 2:12).","l"),
           ("Thyatira",39.095,27.820,"(Rev 2:18).","r"),
           ("Sardis",38.488,28.040,"(Rev 3:1).","l"),
           ("Philadelphia",38.353,28.521,"(Rev 3:7).","r"),
           ("Laodicea",37.834,29.107,"(Rev 3:14).","r")],
   zones=[dict(lat=38.4,lon=27.6,rx=1.7,ry=1.4,label="ASIA")]),
 "mark": dict(title="The Gospel — Galilee to Jerusalem", init=(32.3,35.3,8.0),
   cities=[("Nazareth",32.703,35.297,"Jesus' hometown.","l"),
           ("Capernaum",32.880,35.575,"His Galilean base.","r"),
           ("Jerusalem",31.778,35.235,"Passion, death and resurrection.","r"),
           ("Jericho",31.857,35.444,"On the final road up to Jerusalem.","l")]),
 "genesis": dict(title="Genesis — the way of the patriarchs", init=(33.5,38.0,4.6),
   cities=[("Ur",30.962,46.105,"Abram's starting city in Mesopotamia (Gen 11).","l"),
           ("Haran",36.870,39.035,"Where God called Abram (Gen 11-12).","l"),
           ("Shechem",32.211,35.253,"First stop in the Promised Land; God's promise (Gen 12).","r"),
           ("Bethel",31.930,35.220,"Where Abram built his first altar (Gen 12-13).","l"),
           ("Egypt / Goshen",30.60,31.90,"Where famine drove Abraham — and later Joseph (Gen 12, 41).","l")],
   exodus=[[30.96,46.10],[36.87,39.03],[35.9,36.2],[32.21,35.25],[31.93,35.22],[30.6,31.9]],
   route_label="PATRIARCHS' ROUTE"),
 }

_ALIASES = {
 "romans":["romans"], "ephesians":["ephesians"], "colossians":["colossians"],
 "galatians":["galatians"], "1 peter":["1 peter"], "psalm":["psalm","psalms"],
 "acts":["acts"], "nehemiah":["nehemiah"], "exodus":["exodus"],
 "hebrews":["hebrews"], "corinthians":["corinthians"], "philippians":["philippians"],
 "thessalonians":["thessalonians","thessalonica"], "timothy":["timothy"],
 "titus":["titus"], "philemon":["philemon"], "revelation":["revelation","revelations"],
 "mark":["mark "], "luke":["luke"], "matthew":["matthew"], "john":["john "],
 "genesis":["genesis"],
}
def detect_book(text):
    t = (text or "").lower()
    for key, aliases in _ALIASES.items():
        for a in aliases:
            if a in t:
                return key
    return None

# ================================================================= engine
MAP_CSS = r"""
.mapsection{margin:26px 0}.mapsection .map-body{display:block}
.mapsection .sec-head .bar{background:linear-gradient(90deg,var(--sc-a,var(--ruby)),var(--sc-b,var(--amber)))}
.biblemap{position:relative;background:#0e1116;border:1px solid #373442;border-radius:16px;overflow:hidden}
.bm-vp{position:relative;width:100%;height:500px;overflow:hidden;cursor:grab;touch-action:none;background:#0e1116}
.map-focus .bm-vp{height:430px}
.bm-vp:active{cursor:grabbing}
.tile{position:absolute;will-change:transform;pointer-events:none;user-select:none}
.bm-vec{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}
.bm-vec text.vtext{font-family:'Cormorant Garamond',serif;font-size:26px;letter-spacing:2px;
  stroke:#19181E;stroke-width:5;stroke-linejoin:round;paint-order:stroke}
.bm-vec text.it{font-style:italic}
.bm-markers{position:absolute;top:0;left:0;width:0;height:0}
.marker{position:absolute;transform:translate(-50%,-50%);cursor:pointer;will-change:transform}
.marker .dot{position:absolute;left:-7px;top:-7px;width:14px;height:14px;border-radius:50%;
  background:#C89B3C;border:2.5px solid #19181E;box-shadow:0 0 0 1px rgba(26,26,26,.4)}
.marker.nt .dot{background:#2EC4B6}
.marker.both .dot{background:conic-gradient(#C89B3C 0turn 0.5turn, #2EC4B6 0.5turn 1turn);
  outline:1.5px solid rgba(255,255,255,.22);outline-offset:-1px}
.marker.star .dot{background:#9A2A3E;box-shadow:0 0 0 2px #F2C879,0 0 14px 2px rgba(242,200,121,.5)}
.marker.focus .dot{background:#F2C879;box-shadow:0 0 0 2px rgba(242,200,121,.4),0 0 12px rgba(242,200,121,.55)}
.marker .lbl{position:absolute;white-space:nowrap;font-family:'Inter',sans-serif;font-size:13.5px;font-weight:600;
  color:#F1EDE3;text-shadow:0 1px 2px #000,0 0 4px #000,0 0 8px rgba(0,0,0,.8)}
.marker .lbl.r{left:14px;top:-9px}.marker .lbl.l{right:14px;top:-9px}
.marker:hover .dot{box-shadow:0 0 0 2px #F2C879}
.bm-tip{display:none;position:absolute;left:0;top:0;pointer-events:none;max-width:248px;z-index:6;
  background:#2C2A35;border:1px solid #C89B3C;border-left:3px solid #C89B3C;border-radius:10px;
  padding:9px 12px;font-size:12.5px;line-height:1.5;color:#E6E1D6;box-shadow:0 10px 30px rgba(0,0,0,.55)}
.bm-tip b{display:block;font-family:'Cormorant Garamond',serif;font-size:16px;color:#F2C879;margin-bottom:2px}
.bm-attrib{position:absolute;right:8px;bottom:6px;font-size:10px;color:#cfd4da;background:rgba(10,12,16,.55);
  padding:2px 7px;border-radius:6px;pointer-events:none;z-index:4;letter-spacing:.02em}
.bm-legend{position:absolute;left:10px;bottom:6px;display:flex;gap:14px;align-items:center;z-index:4;
  background:rgba(10,12,16,.78);border:1px solid #3A3744;border-radius:9px;padding:6px 12px;
  font-size:11px;color:#D6DAE0;pointer-events:none;letter-spacing:.02em;flex-wrap:wrap}
.bm-legend-title{flex-direction:column;align-items:flex-start;gap:5px;padding:9px 13px;min-width:150px}
.bm-lg-head{font-family:'Cormorant Garamond',serif;font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:#F2C879;font-weight:600;border-bottom:1px solid #3A3744;padding-bottom:4px;width:100%}
.bm-legend-title>span:not(.bm-lg-head){display:flex;align-items:center;gap:6px}
.bm-legend-title i{margin-right:0}
.bm-legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px;border:1.5px solid #19181E}
.bm-legend i.ot{background:#C89B3C}.bm-legend i.nt{background:#2EC4B6}
.bm-legend i.star{background:#9A2A3E;box-shadow:0 0 0 2px #F2C879}
.bm-legend i.foc{background:#F2C879;box-shadow:0 0 0 2px rgba(242,200,121,.35)}
.bm-legend i.swr{width:18px;height:0;border-top:2px dashed #C89B3C;margin-right:6px;vertical-align:middle;display:inline-block;border-radius:0}
.bm-ctrl{position:absolute;right:10px;top:10px;display:flex;flex-direction:column;gap:6px;z-index:5}
.bm-ctrl button{width:32px;height:32px;border-radius:9px;background:#211F28;border:1px solid #46424F;
  color:#F1EDE3;font-size:17px;line-height:1;cursor:pointer;font-family:'Inter',sans-serif}
.bm-ctrl button:hover{background:#2C2A35;border-color:#6A55B5}
.bm-zoom{font-size:10.5px;text-align:center;color:#A7A09A;padding-top:2px}
.bm-hint{text-align:center;color:#7A746E;font-size:11.5px;padding:8px 10px 10px;border-top:1px solid #373442}
.bm-controls{display:flex;gap:6px}
.bm-toggle{background:#2C2A35;border:1px solid #46424F;color:#A7A09A;border-radius:999px;
  padding:6px 14px;font-size:12.5px;cursor:pointer;transition:.15s;font-family:'Inter',sans-serif}
.bm-toggle:hover{color:#F1EDE3;border-color:#6A55B5}
.bm-toggle.active{background:#4C3A8A;border-color:#6A55B5;color:#F1EDE3}
@media(max-width:640px){.bm-controls{flex-wrap:wrap}.bm-vp{height:380px}.map-focus .bm-vp{height:360px}}
"""

ENGINE_JS = r"""
(function(){
  var D = __DATA__;
  var vp=document.getElementById('bm-vp');
  var tips=document.getElementById('bm-tiles');
  var vecs=document.getElementById('bm-vec');
  var marks=document.getElementById('bm-markers');
  var tip=document.getElementById('bm-tip');
  if(!vp||!tips||!vecs||!marks||!tip) return;

  function merc(lat){ var r=lat*Math.PI/180; return 0.5-Math.asinh(Math.tan(r))/(2*Math.PI); }
  function mercInv(yf){ return Math.atan(Math.sinh(Math.PI*(1-2*yf)))*180/Math.PI; }
  function camPx(){ var ww=256*Math.pow(2,cam.z); return {x:(cam.lon+180)/360*ww, y:merc(cam.lat)*ww, ww:ww}; }
  function clamp(v,a,b){ return v<a?a:(v>b?b:v); }

  var cam = {lon: D.init.lon, lat: D.init.lat, z: D.init.z};
  var MINZ=4, MAXZ=17, vpW, vpH;

  function resize(){ vpW=vp.clientWidth; vpH=vp.clientHeight; render(); }
  window.addEventListener('resize', resize);

  function sx(lon){ var p=camPx(); return (lon+180)/360*p.ww - p.x + vpW/2; }
  function sy(lat){ var p=camPx(); return merc(lat)*p.ww - p.y + vpH/2; }

  var tileCache={}; var curTZ=-1;
  function renderTiles(){
    var zt=Math.floor(cam.z), scale=Math.pow(2,cam.z-zt);
    var ww=256*Math.pow(2,zt);
    var tcx=((cam.lon+180)/360)*ww, tcy=merc(cam.lat)*ww;
    var vpx0=tcx - vpW/2/scale, vpx1=tcx + vpW/2/scale;
    var vpy0=tcy - vpH/2/scale, vpy1=tcy + vpH/2/scale;
    var x0=Math.max(0,Math.floor(vpx0/256)-1), x1=Math.min(Math.pow(2,zt)-1,Math.floor(vpx1/256)+1);
    var y0=Math.max(0,Math.floor(vpy0/256)-1), y1=Math.min(Math.pow(2,zt)-1,Math.floor(vpy1/256)+1);
    if(zt!==curTZ){ for(var k in tileCache){ tileCache[k].parentNode.removeChild(tileCache[k]); } tileCache={}; curTZ=zt; }
    var wanted={};
    for(var y=y0;y<=y1;y++) for(var x=x0;x<=x1;x++){
      var key=zt+':'+x+':'+y; wanted[key]=1;
      var im=tileCache[key];
      if(!im){ im=new Image(); im.className='tile';
        im.src=D.tiles.replace('{z}',zt).replace('{y}',y).replace('{x}',x);
        tips.appendChild(im); tileCache[key]=im; }
      im.style.left=((x*256-tcx)*scale+vpW/2)+'px';
      im.style.top =((y*256-tcy)*scale+vpH/2)+'px';
      im.style.width=(256*scale)+'px'; im.style.height=(256*scale)+'px';
    }
    for(var k in tileCache){ if(!wanted[k]){ tileCache[k].parentNode.removeChild(tileCache[k]); delete tileCache[k]; } }
  }
  tips.style.width='0px'; tips.style.height='0px';

  function poly(pts){ return pts.map(function(p){ return sx(p[1]).toFixed(1)+','+sy(p[0]).toFixed(1); }).join(' '); }
  function renderVectors(){
    var H=[];
    if(D.exodus&&D.exodus.length){
      H.push('<g class="bm-layer" data-era="ot">');
      H.push('<path d="M'+poly(D.exodus)+'" fill="none" stroke="#C89B3C" stroke-width="5" stroke-dasharray="16 14" stroke-linecap="round" opacity="0.95"/>');
      var ex=D.exodus[D.exodus.length-1];
      H.push('<circle cx="'+sx(ex[1]).toFixed(1)+'" cy="'+sy(ex[0]).toFixed(1)+'" r="8" fill="#C89B3C"/>');
      H.push('<text class="vtext" x="'+sx(30.3).toFixed(1)+'" y="'+sy(34.5).toFixed(1)+'" fill="#C89B3C">'+(D.route_label||'EXODUS ROUTE')+'</text>');
      H.push('</g>');
    }
    if(D.boundary&&D.boundary.length){
      H.push('<g class="bm-layer" data-era="ot">');
      D.boundary.forEach(function(seg){ H.push('<path d="M'+poly(seg)+'" fill="none" stroke="#6A55B5" stroke-width="4" stroke-dasharray="9 10" opacity="0.9"/>'); });
      H.push('</g>');
    }
    if(D.nt_path&&D.nt_path.length){
      H.push('<g class="bm-layer" data-era="nt">');
      var g=D.galilee;
      if(g) H.push('<ellipse cx="'+sx(g.lon).toFixed(1)+'" cy="'+sy(g.lat).toFixed(1)+'" rx="'+Math.abs(sx(g.lon-g.rx)-sx(g.lon+g.rx))/2+'" ry="'+Math.abs(sy(g.lat+g.ry)-sy(g.lat-g.ry))/2+'" fill="#5F7A55" opacity="0.16"/>');
      H.push('<path d="M'+poly(D.nt_path)+'" fill="none" stroke="#F2C879" stroke-width="4" stroke-dasharray="13 12" stroke-linecap="round" opacity="0.95"/>');
      H.push('<text class="vtext" x="'+sx(32.60).toFixed(1)+'" y="'+sy(35.08).toFixed(1)+'" fill="#F2C879">TO JERUSALEM</text>');
      H.push('</g>');
    }
    (D.regions||[]).forEach(function(x){
      var ang=x[3]?' transform="rotate('+x[3]+' '+sx(x[2]).toFixed(1)+' '+sy(x[1]).toFixed(1)+')"':'';
      H.push('<text class="vtext it" x="'+sx(x[2]).toFixed(1)+'" y="'+sy(x[1]).toFixed(1)+'" fill="'+x[4]+'"'+ang+'>'+x[0]+'</text>');
    });
    (D.waters||[]).forEach(function(w){
      H.push('<ellipse cx="'+sx(w[1]).toFixed(1)+'" cy="'+sy(w[0]).toFixed(1)+'" rx="'+Math.abs(sx(w[1]+w[2])-sx(w[1]-w[2]))/2+'" ry="'+Math.abs(sy(w[0]+w[3])-sy(w[0]-w[3]))/2+'" fill="none" stroke="#9ED4E0" stroke-width="2.5" stroke-dasharray="8 8" opacity="0.85"/>');
      H.push('<text class="vtext it" x="'+sx(w[1]).toFixed(1)+'" y="'+sy(w[0]).toFixed(1)+'" fill="#9ED4E0" text-anchor="middle">'+w[4]+'</text>');
    });
    if(D.jordan&&D.jordan.length)
      H.push('<path d="M'+poly(D.jordan)+'" fill="none" stroke="#9ED4E0" stroke-width="4" stroke-dasharray="10 9" opacity="0.9"/>');
    (D.zones||[]).forEach(function(z){
      H.push('<ellipse cx="'+sx(z.lon).toFixed(1)+'" cy="'+sy(z.lat).toFixed(1)+'" rx="'+Math.abs(sx(z.lon-z.rx)-sx(z.lon+z.rx))/2+'" ry="'+Math.abs(sy(z.lat+z.ry)-sy(z.lat-z.ry))/2+'" fill="#C89B3C" opacity="0.10" stroke="#C89B3C" stroke-opacity="0.4" stroke-dasharray="6 6"/>');
      if(z.label) H.push('<text class="vtext it" x="'+sx(z.lon).toFixed(1)+'" y="'+sy(z.lat).toFixed(1)+'" fill="#F2C879" text-anchor="middle">'+z.label+'</text>');
    });
    (D.routes||[]).forEach(function(r){
      var c=r.color||'#C89B3C';
      H.push('<path d="M'+poly(r.pts)+'" fill="none" stroke="'+c+'" stroke-width="4" stroke-dasharray="11 10" stroke-linecap="round" opacity="0.9"/>');
      if(r.label&&r.label_pt) H.push('<text class="vtext" x="'+sx(r.label_pt[1]).toFixed(1)+'" y="'+sy(r.label_pt[0]).toFixed(1)+'" fill="'+c+'">'+r.label+'</text>');
    });
    vecs.innerHTML=H.join('');
  }

  var cities=[];
  function buildMarkers(){
    marks.innerHTML='';
    D.cities.forEach(function(c){
      var m=document.createElement('div');
      var cls = c[1]==='ot'?' ot':(c[1]==='nt'?' nt':(c[1]==='both'?' both':' focus'));
      m.className='marker'+cls;
      m.setAttribute('data-era',c[1]||'all');
      m.setAttribute('data-name',c[0]);
      m.setAttribute('data-note',c[4]);
      var dot=document.createElement('i'); dot.className='dot';
      if(c[0]==='Jerusalem'&&c[1]==='both') dot.className='dot star';
      var lbl=document.createElement('span'); lbl.className='lbl'+(c[5]||'r');
      lbl.textContent=c[0];
      m.appendChild(dot); m.appendChild(lbl); m.__c=c;
      marks.appendChild(m); cities.push(m);
      m.addEventListener('mouseenter',function(e){showTip(e,this)});
      m.addEventListener('mousemove',function(e){moveTip(e)});
      m.addEventListener('mouseleave',function(){tip.style.display='none'});
    });
    renderMarkers();
  }
  function renderMarkers(){
    for(var i=0;i<cities.length;i++){ var m=cities[i], c=m.__c;
      m.style.left=sx(c[3]).toFixed(1)+'px'; m.style.top=sy(c[2]).toFixed(1)+'px';
    }
  }
  function showTip(e,m){
    // SAFE: data-name/note are static attributes generated from a hard-coded list.
    tip.innerHTML='<b>'+m.getAttribute('data-name')+'</b>'+m.getAttribute('data-note');
    tip.style.display='block'; moveTip(e);
  }
  function moveTip(e){
    var r=vp.getBoundingClientRect(), t=tip.getBoundingClientRect();
    var x=e.clientX-r.left+16, y=e.clientY-r.top-10;
    if(x+t.width>vpW-8) x=e.clientX-r.left-t.width-16;
    if(y+t.height>vpH-8) y=e.clientY-r.top-t.height+16;
    tip.style.left=Math.max(6,x)+'px'; tip.style.top=Math.max(6,y)+'px';
  }

  function apply(era){
    if(!document.querySelectorAll('.bm-toggle').length) return;
    document.querySelectorAll('.bm-toggle').forEach(function(b){ b.classList.toggle('active',b.getAttribute('data-era')===era); });
    cities.forEach(function(m){ m.style.display=era==='all'||m.getAttribute('data-era')===era?'':'none'; });
    vecs.querySelectorAll('.bm-layer').forEach(function(g){ g.style.display=era==='all'||g.getAttribute('data-era')===era?'':'none'; });
  }
  document.querySelectorAll('.bm-toggle').forEach(function(b){
    b.addEventListener('click',function(){ apply(this.getAttribute('data-era')); });
  });

  function pan(dx,dy){ var p=camPx(); p.x+=dx; p.y+=dy;
    cam.lon=p.x/p.ww*360-180; cam.lat=mercInv(p.y/p.ww); render(); }
  function zoomAt(mx,my,f){
    var p=camPx();
    var lon0=(p.x+(mx-vpW/2))/p.ww*360-180;
    var lat0=mercInv((p.y+(my-vpH/2))/p.ww);
    var z2=clamp(cam.z+Math.log2(f),MINZ,MAXZ);
    var q=256*Math.pow(2,z2);
    cam.z=z2; cam.lon=lon0+(vpW/2-mx)/q*360; cam.lat=mercInv(merc(lat0)+(vpH/2-my)/q);
    render();
  }
  var drag=null, pd=null;
  function render(){
    if(!vpW) return;
    renderTiles(); renderVectors(); renderMarkers();
    var zde=document.getElementById('bm-zoom'); if(zde) zde.textContent='z'+Math.round(cam.z*10)/10;
  }

  vp.addEventListener('mousedown',function(e){
    if(e.button!==0) return;
    if(e.target.closest('button')) return;
    drag={x:e.clientX,y:e.clientY}; e.preventDefault();
  });
  window.addEventListener('mousemove',function(e){
    if(drag){ pan(drag.x-e.clientX, drag.y-e.clientY); drag={x:e.clientX,y:e.clientY}; }
  });
  window.addEventListener('mouseup',function(){ drag=null; });
  vp.addEventListener('wheel',function(e){
    e.preventDefault();
    var r=vp.getBoundingClientRect();
    zoomAt(e.clientX-r.left,e.clientY-r.top, Math.pow(2,-e.deltaY*0.0022));
  },{passive:false});
  vp.addEventListener('dblclick',function(e){
    var r=vp.getBoundingClientRect(); zoomAt(e.clientX-r.left,e.clientY-r.top,2);
  });
  vp.addEventListener('touchstart',function(e){
    if(e.touches.length===1){ pd={x:e.touches[0].clientX,y:e.touches[0].clientY,d:0}; }
    else if(e.touches.length===2){ var t1=e.touches[0],t2=e.touches[1];
      pd={x:(t1.clientX+t2.clientX)/2,y:(t1.clientY+t2.clientY)/2,d:Math.hypot(t1.clientX-t2.clientX,t1.clientY-t2.clientY)}; }
    e.preventDefault();
  },{passive:false});
  vp.addEventListener('touchmove',function(e){
    e.preventDefault();
    if(e.touches.length===1&&pd&&!pd.d){ pan(pd.x-e.touches[0].clientX, pd.y-e.touches[0].clientY); pd={x:e.touches[0].clientX,y:e.touches[0].clientY,d:0}; }
    else if(e.touches.length===2&&pd&&pd.d){
      var t1=e.touches[0],t2=e.touches[1];
      var nx=(t1.clientX+t2.clientX)/2, ny=(t1.clientY+t2.clientY)/2;
      var nd=Math.hypot(t1.clientX-t2.clientX,t1.clientY-t2.clientY);
      var rr=vp.getBoundingClientRect(); zoomAt(nx-rr.left, ny-rr.top, nd/pd.d); pd.d=nd;
    }
  },{passive:false});
  vp.addEventListener('touchend',function(){ pd=null; });

  var zp=document.getElementById('bm-zoomin'), zm=document.getElementById('bm-zoomout'), zr=document.getElementById('bm-reset');
  if(zp) zp.addEventListener('click',function(){ zoomAt(vpW/2,vpH/2,1.6); });
  if(zm) zm.addEventListener('click',function(){ zoomAt(vpW/2,vpH/2,1/1.6); });
  if(zr) zr.addEventListener('click',function(){ cam.lon=D.init.lon; cam.lat=D.init.lat; cam.z=D.init.z; drag=null; render(); });

  buildMarkers(); apply('all'); resize();
})();
"""

def json_d(o): return json.dumps(o, ensure_ascii=False)

def focus_legend(data):
    """A small legend for focus (per-sermon) maps, built from the data."""
    items = ['<span><i class="foc"></i>Key place</span>']
    for r in (data.get("routes") or []):
        c = r.get("color", "#C89B3C")
        items.append(f'<span><i class="swr" style="border-top:2px dashed {c}"></i>{r.get("label","Route")}</span>')
    if any((c[0] == "Jerusalem" and c[1] == "focus") for c in data.get("cities", [])):
        items.append('<span><i class="star"></i>Jerusalem</span>')
    return "".join(items)

def render_block(title, data, toggles=False, legend=None, focus=False, hint=None):
    togg = ('<div class="bm-controls">'
            '<button class="bm-toggle" data-era="all">All eras</button>'
            '<button class="bm-toggle" data-era="ot">Old Testament</button>'
            '<button class="bm-toggle" data-era="nt">New Testament</button></div>') if toggles else ""
    if legend and legend is not True:
        legg = f'<div class="bm-legend">{legend}</div>'
    elif legend is True:
        legg = ('<div class="bm-legend bm-legend-title">'
                '<span class="bm-lg-head">Legend</span>'
                '<span><i class="ot"></i>Old Testament</span>'
                '<span><i class="nt"></i>New Testament</span>'
                '<span><i class="star"></i>Jerusalem</span></div>')
    else:
        legg = ""
    if hint is None:
        hint = "Drag to pan · scroll / pinch to zoom · double-click to zoom in · hover a marker for a note"
    cls = "mapsection map-focus" if focus else "mapsection"
    return f"""<section class="{cls}">
  <div class="sec-head"><div class="left"><span class="bar"></span><h2>{title}</h2></div>{togg}</div>
  <div class="biblemap">
    <div class="bm-vp" id="bm-vp">
      <div id="bm-tiles"></div>
      <svg class="bm-vec" id="bm-vec"></svg>
      <div class="bm-markers" id="bm-markers"></div>
      <div class="bm-ctrl">
        <button id="bm-zoomin" title="Zoom in">+</button>
        <button id="bm-zoomout" title="Zoom out">−</button>
        <button id="bm-reset" title="Reset view">⟳</button>
        <div class="bm-zoom" id="bm-zoom"></div>
      </div>
      <div class="bm-attrib">Imagery © Esri World Imagery</div>
      {legg}
    </div>
    <div class="bm-tip" id="bm-tip"></div>
    <div class="bm-hint">{hint}</div>
  </div>
</section>
<style>{MAP_CSS}</style>
<script>{ENGINE_JS.replace("__DATA__", json_d(data))}</script>
"""

def overview_block():
    return render_block("The Bible Lands", OVERVIEW, toggles=True, legend=True)

def sermon_map_block(book_key):
    b = BOOKS[book_key]
    init = {"lat": b["init"][0], "lon": b["init"][1], "z": b["init"][2]}
    cities = [(n, "focus", la, lo, note, s) for (n, la, lo, note, s) in b["cities"]]
    data = _d(init, cities, zones=b.get("zones", []), exodus=b.get("exodus", []),
              routes=b.get("routes", []))
    return render_block(b["title"], data, toggles=False, legend=focus_legend(data),
                        focus=True, hint="Drag to pan · scroll to zoom · hover a marker for a note")

def main():
    open(os.path.join(PROJ, "map-block.html"), "w", encoding="utf-8").write(overview_block())
    print(f"[map] overview block written; {len(BOOKS)} book-focus maps available: {', '.join(BOOKS)}")

if __name__ == "__main__":
    main()
