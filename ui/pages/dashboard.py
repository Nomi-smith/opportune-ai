import streamlit as st

from ui import components as c

CATEGORIES = [
    ("🎓", "Scholarships", "Funding, fellowships and grants", c.NAV_SCHOLARSHIPS),
    ("💼", "Jobs", "International and local jobs, one card per posting", c.NAV_JOBS),
    ("🧑‍💻", "Internships", "Internships and trainee roles", c.NAV_INTERNSHIPS),
    ("🏛️", "Admissions", "Master's and study opportunities", c.NAV_ADMISSIONS),
    ("🔬", "Research", "Research positions and funding", c.NAV_RESEARCH),
    ("🤖", "AI Agent", "Ask naturally and let the agent search", c.NAV_AGENT),
]

# Official / major portals only. DAAD links straight to its scholarship database.
PORTAL_GROUPS = {
    "Scholarships": [
        ("DAAD", "German Academic Exchange Service — scholarship database",
         "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"),
        ("Erasmus+", "Erasmus Mundus Joint Master's opportunities",
         "https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters"),
        ("Chevening", "UK government global scholarships", "https://www.chevening.org/"),
        ("Commonwealth Scholarships", "UK Commonwealth Scholarship Commission", "https://cscuk.fcdo.gov.uk/scholarships/"),
        ("Fulbright", "US government exchange programme", "https://foreign.fulbrightonline.org/"),
        ("Swedish Institute", "Scholarships for global professionals", "https://si.se/en/apply/scholarships/"),
        ("Türkiye Bursları", "Turkish government scholarships", "https://turkiyeburslari.gov.tr/en"),
        ("Campus China (CSC)", "Chinese Government Scholarship", "https://www.campuschina.org/"),
        ("Stipendium Hungaricum", "Hungarian government scholarships", "https://stipendiumhungaricum.hu/"),
        ("Study in Korea (GKS)", "Global Korea Scholarship", "https://www.studyinkorea.go.kr/en/main.do"),
        ("Study in Japan", "MEXT and other Japan scholarships", "https://www.studyinjapan.go.jp/en/"),
        ("Gates Cambridge", "Postgraduate scholarships at Cambridge", "https://www.gatescambridge.org/"),
    ],
    "Study abroad": [
        ("Study in Denmark", "Official guide to studying in Denmark", "https://studyindenmark.dk/"),
        ("Study in Sweden", "Official guide to studying in Sweden", "https://studyinsweden.se/"),
        ("Study in Europe", "European Commission study portal", "https://education.ec.europa.eu/study-in-europe"),
        ("Study in Germany", "DAAD portal for international students", "https://www.study-in-germany.de/en/"),
        ("Study in Finland", "Official guide to studying in Finland", "https://www.studyinfinland.fi/"),
        ("Study in Norway", "Official guide to studying in Norway", "https://www.studyinnorway.no/"),
        ("Study in Holland", "Official Dutch study portal", "https://www.studyinholland.nl/"),
        ("Campus France", "Study in France", "https://www.campusfrance.org/en"),
        ("Study UK", "British Council study portal", "https://study-uk.britishcouncil.org/"),
        ("EducationUSA", "US Department of State advising network", "https://educationusa.state.gov/"),
        ("Study Australia", "Australian Government study portal", "https://www.studyaustralia.gov.au/en"),
        ("EduCanada", "Official Canadian study portal", "https://www.educanada.ca/"),
    ],
    "Jobs": [
        ("EURES", "European job mobility portal", "https://eures.europa.eu/index_en"),
        ("Make it in Germany", "Official portal for working in Germany",
         "https://www.make-it-in-germany.com/en/working-in-germany/job/looking-for-job"),
        ("Arbeitsagentur", "German Federal Employment Agency", "https://www.arbeitsagentur.de/jobsuche/"),
        ("Job Bank Canada", "Government of Canada job board", "https://www.jobbank.gc.ca/"),
        ("USAJOBS", "US federal government jobs", "https://www.usajobs.gov/"),
        ("UN Careers", "United Nations jobs and internships", "https://careers.un.org/"),
        ("Remotive", "Remote jobs worldwide", "https://remotive.com/"),
        ("Arbeitnow", "Jobs in Germany and Europe", "https://www.arbeitnow.com/"),
    ],
    "Research": [
        ("EURAXESS", "Research jobs and funding across Europe", "https://euraxess.ec.europa.eu/jobs"),
        ("Marie Skłodowska-Curie", "EU research fellowships", "https://marie-sklodowska-curie-actions.ec.europa.eu/"),
        ("Academic Positions", "Academic and research jobs", "https://academicpositions.com/"),
        ("jobs.ac.uk", "Academic jobs in the UK and beyond", "https://www.jobs.ac.uk/"),
        ("FindAPhD", "PhD programmes and funding", "https://www.findaphd.com/"),
        ("Nature Careers", "Science jobs and funding", "https://www.nature.com/naturecareers"),
        ("Google PhD Fellowship", "Fellowship for computer science PhDs", "https://research.google/programs-and-events/phd-fellowship/"),
    ],
}
PORTALS = [row for rows in PORTAL_GROUPS.values() for row in rows]


def render():
    st.markdown(
        '<div class="oa-hero"><h1>Find your next opportunity</h1>'
        "<p>Search scholarships, jobs, internships, admissions and research opportunities from trusted sources.</p></div>",
        unsafe_allow_html=True,
    )

    for row_start in range(0, len(CATEGORIES), 3):
        cols = st.columns(3)
        for col, (emoji, title, subtitle, target) in zip(cols, CATEGORIES[row_start:row_start + 3]):
            with col, st.container(border=True):
                st.markdown(
                    f'<div class="oa-icon">{emoji}</div><div class="oa-card-title">{title}</div>'
                    f'<div class="oa-card-sub">{subtitle}</div>',
                    unsafe_allow_html=True,
                )
                st.button("Open", key=f"dash_{title}", on_click=c.go_to, args=(target,), use_container_width=True)

    st.markdown('<div class="oa-section">Trusted source portals</div>', unsafe_allow_html=True)
    st.caption("Official portals you can browse directly. Opportune AI also searches them and verifies each source page.")
    tabs = st.tabs(list(PORTAL_GROUPS))
    for tab, rows in zip(tabs, PORTAL_GROUPS.values()):
        with tab:
            for row_start in range(0, len(rows), 4):
                cols = st.columns(4)
                for col, (name, blurb, url) in zip(cols, rows[row_start:row_start + 4]):
                    with col, st.container(border=True):
                        st.markdown(f"**{name}**")
                        st.caption(blurb)
                        st.link_button("Visit ↗", url, use_container_width=True)
