"""Country-aware source priorities for global opportunity discovery.

Domains are used as search hints and ranking signals, not as an exclusive
allow-list. Broad web discovery remains enabled after preferred sources.
"""

COUNTRY_SOURCES = {
    "Germany": {
        "study": ["hochschulkompass.de", "daad.de", "make-it-in-germany.com"],
        "scholarship": ["daad.de", "deutschlandstipendium.de", "stipendiumplus.de"],
        "research": ["euraxess.de", "daad.de", "dfg.de"],
        "job": ["arbeitsagentur.de", "make-it-in-germany.com", "eures.europa.eu"],
        "internship": ["arbeitsagentur.de", "make-it-in-germany.com", "eures.europa.eu"],
    },
    "Netherlands": {
        "study": ["studyinnl.org", "studielink.nl", "nuffic.nl"],
        "scholarship": ["studyinnl.org", "nuffic.nl"],
        "research": ["academictransfer.com", "nwo.nl", "euraxess.nl"],
        "job": ["werk.nl", "uwv.nl", "eures.europa.eu"],
        "internship": ["werk.nl", "eures.europa.eu"],
    },
    "Sweden": {
        "study": ["universityadmissions.se", "studyinsweden.se"],
        "scholarship": ["studyinsweden.se", "si.se"],
        "research": ["euraxess.se", "vr.se"],
        "job": ["arbetsformedlingen.se", "eures.europa.eu"],
        "internship": ["arbetsformedlingen.se", "eures.europa.eu"],
    },
    "Finland": {
        "study": ["studyinfo.fi", "opintopolku.fi", "studyinfinland.fi"],
        "scholarship": ["studyinfo.fi", "studyinfinland.fi"],
        "research": ["aka.fi", "research.fi", "euraxess.fi"],
        "job": ["tyomarkkinatori.fi", "jobmarketfinland.fi", "eures.europa.eu"],
        "internship": ["tyomarkkinatori.fi", "jobmarketfinland.fi"],
    },
    "Denmark": {
        "study": ["studyindenmark.dk", "ufm.dk"],
        "scholarship": ["studyindenmark.dk", "ufm.dk"],
        "research": ["jobindex.dk", "euraxess.dk", "ufm.dk"],
        "job": ["workindenmark.dk", "jobnet.dk", "eures.europa.eu"],
        "internship": ["workindenmark.dk", "jobnet.dk"],
    },
    "Norway": {
        "study": ["studyinnorway.no", "samordnaopptak.no"],
        "scholarship": ["studyinnorway.no", "hkdir.no"],
        "research": ["forskningsradet.no", "jobbnorge.no", "euraxess.no"],
        "job": ["nav.no", "arbeidsplassen.nav.no", "eures.europa.eu"],
        "internship": ["nav.no", "arbeidsplassen.nav.no"],
    },
    "France": {
        "study": ["campusfrance.org", "monmaster.gouv.fr", "parcoursup.gouv.fr"],
        "scholarship": ["campusfrance.org", "enseignementsup-recherche.gouv.fr"],
        "research": ["euraxess.fr", "cnrs.fr", "anr.fr"],
        "job": ["francetravail.fr", "service-public.fr", "eures.europa.eu"],
        "internship": ["francetravail.fr", "eures.europa.eu"],
    },
    "Italy": {
        "study": ["universitaly.it", "mur.gov.it"],
        "scholarship": ["universitaly.it", "mur.gov.it"],
        "research": ["euraxess.it", "cnr.it", "infn.it"],
        "job": ["anpal.gov.it", "inpa.gov.it", "eures.europa.eu"],
        "internship": ["anpal.gov.it", "inpa.gov.it"],
    },
    "Spain": {
        "study": ["universidades.gob.es", "unedasiss.uned.es"],
        "scholarship": ["becaseducacion.gob.es", "universidades.gob.es"],
        "research": ["euraxess.es", "csic.es"],
        "job": ["sepe.es", "eures.europa.eu"],
        "internship": ["sepe.es", "eures.europa.eu"],
    },
    "Portugal": {
        "study": ["dges.gov.pt", "studyinportugal.edu.gov.pt"],
        "scholarship": ["dges.gov.pt", "fct.pt"],
        "research": ["fct.pt", "euraxess.pt"],
        "job": ["iefp.pt", "eures.europa.eu"],
        "internship": ["iefp.pt", "eures.europa.eu"],
    },
    "Austria": {
        "study": ["studienwahl.at", "oead.at"],
        "scholarship": ["grants.at", "oead.at"],
        "research": ["euraxess.at", "fwf.ac.at"],
        "job": ["ams.at", "eures.europa.eu"],
        "internship": ["ams.at", "eures.europa.eu"],
    },
    "Switzerland": {
        "study": ["swissuniversities.ch", "swiss-scholarships.ch"],
        "scholarship": ["swissuniversities.ch", "sbfi.admin.ch"],
        "research": ["swissuniversities.ch", "snf.ch", "euraxess.ch"],
        "job": ["job-room.ch", "arbeit.swiss", "eures.europa.eu"],
        "internship": ["job-room.ch", "arbeit.swiss"],
    },
    "Belgium": {
        "study": ["studyinbelgium.be", "studyinflanders.be", "mesetudes.be"],
        "scholarship": ["studyinbelgium.be", "ares-ac.be"],
        "research": ["euraxess.be", "fnrs.be", "fwo.be"],
        "job": ["leforem.be", "vdab.be", "actiris.brussels", "eures.europa.eu"],
        "internship": ["vdab.be", "leforem.be", "actiris.brussels"],
    },
    "United Kingdom": {
        "study": ["ucas.com", "gov.uk", "study-uk.britishcouncil.org"],
        "scholarship": ["study-uk.britishcouncil.org", "gov.uk", "chevening.org"],
        "research": ["jobs.ac.uk", "ukri.org", "euraxess.ec.europa.eu"],
        "job": ["gov.uk", "findajob.dwp.gov.uk", "jobs.ac.uk"],
        "internship": ["gov.uk", "findajob.dwp.gov.uk", "jobs.ac.uk"],
    },
    "Ireland": {
        "study": ["educationinireland.com", "cao.ie", "gov.ie"],
        "scholarship": ["hea.ie", "educationinireland.com", "gov.ie"],
        "research": ["research.ie", "euraxess.ie", "hea.ie"],
        "job": ["jobsireland.ie", "gov.ie", "eures.europa.eu"],
        "internship": ["jobsireland.ie", "eures.europa.eu"],
    },
    "Poland": {
        "study": ["study.gov.pl", "nawa.gov.pl"],
        "scholarship": ["nawa.gov.pl", "study.gov.pl"],
        "research": ["ncn.gov.pl", "nawa.gov.pl", "euraxess.pl"],
        "job": ["praca.gov.pl", "eures.europa.eu"],
        "internship": ["praca.gov.pl", "eures.europa.eu"],
    },
    "Czech Republic": {
        "study": ["studyin.cz", "msmt.gov.cz"],
        "scholarship": ["studyin.cz", "msmt.gov.cz"],
        "research": ["czechinvest.org", "gacr.cz", "euraxess.cz"],
        "job": ["uradprace.cz", "eures.europa.eu"],
        "internship": ["uradprace.cz", "eures.europa.eu"],
    },
    "Hungary": {
        "study": ["studyinhungary.hu", "tka.hu"],
        "scholarship": ["stipendiumhungaricum.hu", "tka.hu"],
        "research": ["nkfih.gov.hu", "euraxess.hu"],
        "job": ["munka.hu", "eures.europa.eu"],
        "internship": ["munka.hu", "eures.europa.eu"],
    },
    "Türkiye": {
        "study": ["studyinturkiye.gov.tr", "yok.gov.tr"],
        "scholarship": ["turkiyeburslari.gov.tr", "ytb.gov.tr"],
        "research": ["tubitak.gov.tr", "yok.gov.tr"],
        "job": ["iskur.gov.tr", "kariyerkapisi.gov.tr"],
        "internship": ["kariyerkapisi.gov.tr", "iskur.gov.tr"],
    },
    "Romania": {
        "study": ["studyinromania.gov.ro", "edu.ro"],
        "scholarship": ["studyinromania.gov.ro", "edu.ro"],
        "research": ["uefiscdi.gov.ro", "euraxess.ro"],
        "job": ["anofm.ro", "eures.europa.eu"],
        "internship": ["anofm.ro", "eures.europa.eu"],
    },
    "Estonia": {
        "study": ["studyinestonia.ee", "harno.ee"],
        "scholarship": ["harno.ee", "studyinestonia.ee"],
        "research": ["etag.ee", "euraxess.ee"],
        "job": ["tootukassa.ee", "eures.europa.eu"],
        "internship": ["tootukassa.ee", "eures.europa.eu"],
    },
    "Latvia": {
        "study": ["studyinlatvia.lv", "izm.gov.lv"],
        "scholarship": ["viaa.gov.lv", "studyinlatvia.lv"],
        "research": ["lzp.gov.lv", "euraxess.lv"],
        "job": ["nva.gov.lv", "eures.europa.eu"],
        "internship": ["nva.gov.lv", "eures.europa.eu"],
    },
    "Lithuania": {
        "study": ["studyin.lt", "smsm.lrv.lt"],
        "scholarship": ["studyin.lt", "vsf.lrv.lt"],
        "research": ["lmt.lt", "euraxess.lt"],
        "job": ["uzt.lt", "eures.europa.eu"],
        "internship": ["uzt.lt", "eures.europa.eu"],
    },
    "Greece": {
        "study": ["studyingreece.edu.gr", "minedu.gov.gr"],
        "scholarship": ["iky.gr", "minedu.gov.gr"],
        "research": ["gsri.gov.gr", "euraxess.gr"],
        "job": ["dypa.gov.gr", "eures.europa.eu"],
        "internship": ["dypa.gov.gr", "eures.europa.eu"],
    },
    "United States": {
        "study": ["educationusa.state.gov", "studentaid.gov"],
        "scholarship": ["studentaid.gov", "educationusa.state.gov"],
        "research": ["nsf.gov", "nih.gov", "usajobs.gov"],
        "job": ["usajobs.gov", "dol.gov"],
        "internship": ["usajobs.gov", "dol.gov"],
    },
    "Canada": {
        "study": ["educanada.ca", "canada.ca"],
        "scholarship": ["educanada.ca", "canada.ca"],
        "research": ["nserc-crsng.gc.ca", "cihr-irsc.gc.ca", "sshrc-crsh.canada.ca"],
        "job": ["jobbank.gc.ca", "canada.ca"],
        "internship": ["jobbank.gc.ca", "canada.ca"],
    },
    "Australia": {
        "study": ["studyaustralia.gov.au", "education.gov.au"],
        "scholarship": ["studyaustralia.gov.au", "dfat.gov.au"],
        "research": ["arc.gov.au", "nhmrc.gov.au"],
        "job": ["workforceaustralia.gov.au", "jobs.gov.au"],
        "internship": ["workforceaustralia.gov.au", "jobs.gov.au"],
    },
    "New Zealand": {
        "study": ["studywithnewzealand.govt.nz", "education.govt.nz"],
        "scholarship": ["nzscholarships.govt.nz", "studywithnewzealand.govt.nz"],
        "research": ["royalsociety.org.nz", "mbie.govt.nz"],
        "job": ["seek.co.nz", "jobs.govt.nz", "careers.govt.nz"],
        "internship": ["careers.govt.nz", "jobs.govt.nz"],
    },
    "Japan": {
        "study": ["studyinjapan.go.jp", "jasso.go.jp"],
        "scholarship": ["mext.go.jp", "jasso.go.jp", "studyinjapan.go.jp"],
        "research": ["jsps.go.jp", "jst.go.jp"],
        "job": ["hellowork.mhlw.go.jp", "jsite.mhlw.go.jp"],
        "internship": ["jsite.mhlw.go.jp", "jasso.go.jp"],
    },
    "South Korea": {
        "study": ["studyinkorea.go.kr", "moe.go.kr"],
        "scholarship": ["studyinkorea.go.kr", "korea.net"],
        "research": ["nrf.re.kr", "kistep.re.kr"],
        "job": ["work.go.kr", "moel.go.kr"],
        "internship": ["work.go.kr", "moel.go.kr"],
    },
    "China": {
        "study": ["campuschina.org", "moe.gov.cn"],
        "scholarship": ["campuschina.org", "csc.edu.cn"],
        "research": ["nsfc.gov.cn", "cas.cn"],
        "job": ["gov.cn", "mohrss.gov.cn"],
        "internship": ["gov.cn", "mohrss.gov.cn"],
    },
    "Singapore": {
        "study": ["moe.gov.sg", "nus.edu.sg", "ntu.edu.sg"],
        "scholarship": ["moe.gov.sg", "nus.edu.sg", "ntu.edu.sg"],
        "research": ["a-star.edu.sg", "nus.edu.sg", "ntu.edu.sg"],
        "job": ["mycareersfuture.gov.sg", "careers.gov.sg"],
        "internship": ["mycareersfuture.gov.sg", "careers.gov.sg"],
    },
    "Malaysia": {
        "study": ["educationmalaysia.gov.my", "mohe.gov.my"],
        "scholarship": ["educationmalaysia.gov.my", "mohe.gov.my"],
        "research": ["mosti.gov.my", "mynresearch.com"],
        "job": ["myfuturejobs.gov.my", "mohr.gov.my"],
        "internship": ["myfuturejobs.gov.my", "mohr.gov.my"],
    },
    "United Arab Emirates": {
        "study": ["u.ae", "mohesr.gov.ae"],
        "scholarship": ["u.ae", "mohesr.gov.ae"],
        "research": ["uaeu.ac.ae", "mbzuai.ac.ae"],
        "job": ["u.ae", "mohre.gov.ae"],
        "internship": ["u.ae", "mohre.gov.ae"],
    },
    "Saudi Arabia": {
        "study": ["studyinsaudi.moe.gov.sa", "moe.gov.sa"],
        "scholarship": ["studyinsaudi.moe.gov.sa", "moe.gov.sa"],
        "research": ["kacst.gov.sa", "kau.edu.sa"],
        "job": ["hrsd.gov.sa", "jadarat.sa"],
        "internship": ["jadarat.sa", "hrsd.gov.sa"],
    },
    "Qatar": {
        "study": ["studyinqatar.edu.gov.qa", "edu.gov.qa"],
        "scholarship": ["edu.gov.qa", "qu.edu.qa"],
        "research": ["qf.org.qa", "qu.edu.qa"],
        "job": ["gov.qa", "hukoomi.gov.qa"],
        "internship": ["gov.qa", "hukoomi.gov.qa"],
    },
    "Pakistan": {
        "study": ["hec.gov.pk", "education.gov.pk"],
        "scholarship": ["hec.gov.pk", "scholarships.hec.gov.pk"],
        "research": ["hec.gov.pk", "psf.gov.pk", "pc.gov.pk"],
        "job": ["njp.gov.pk", "rozee.pk", "mustakbil.com"],
        "internship": ["njp.gov.pk", "rozee.pk", "mustakbil.com"],
    },
    "India": {
        "study": ["studyinindia.gov.in", "education.gov.in"],
        "scholarship": ["scholarships.gov.in", "education.gov.in"],
        "research": ["dst.gov.in", "anrfonline.in", "ugc.gov.in"],
        "job": ["ncs.gov.in", "gov.in"],
        "internship": ["internship.aicte-india.org", "ncs.gov.in"],
    },
    "South Africa": {
        "study": ["dhet.gov.za", "studysa.org"],
        "scholarship": ["nsfas.org.za", "dhet.gov.za"],
        "research": ["nrf.ac.za", "dsti.gov.za"],
        "job": ["labour.gov.za", "gov.za"],
        "internship": ["gov.za", "labour.gov.za"],
    },
    "Brazil": {
        "study": ["gov.br", "mec.gov.br", "gov.br/capes"],
        "scholarship": ["capes.gov.br", "cnpq.br"],
        "research": ["cnpq.br", "fapesp.br", "capes.gov.br"],
        "job": ["gov.br/trabalho", "gov.br"],
        "internship": ["gov.br", "ciee.org.br"],
    },
}

# Common cross-border sources. They are secondary to country-specific official sources.
CROSS_BORDER = {
    "study": ["education.ec.europa.eu", "erasmus-plus.ec.europa.eu"],
    "scholarship": ["erasmus-plus.ec.europa.eu", "euraxess.ec.europa.eu"],
    "research": ["euraxess.ec.europa.eu", "cordis.europa.eu"],
    "job": ["eures.europa.eu"],
    "internship": ["eures.europa.eu"],
}


def category_for(opportunity_type):
    value = (opportunity_type or "").strip().lower()
    if value == "master's":
        return "study"
    return value if value in {"job", "internship", "scholarship", "research", "study"} else "study"


def preferred_domains(country, opportunity_type):
    country = (country or "").strip()
    category = category_for(opportunity_type)
    specific = COUNTRY_SOURCES.get(country, {}).get(category, [])
    cross = CROSS_BORDER.get(category, [])
    out=[]
    for domain in specific + cross:
        if domain not in out:
            out.append(domain)
    return out
