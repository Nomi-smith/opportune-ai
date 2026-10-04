from datetime import date, timedelta
from intelligence.freshness import availability_reason
from models.opportunity import Opportunity

def test_expired_opportunity_rejected():
    item=Opportunity(title='Old Scholarship',organization='X',opportunity_type='SCHOLARSHIP',deadline='2024-08-01',description='Scholarship')
    ok,_=availability_reason(item)
    assert not ok

def test_current_opportunity_accepted():
    d=(date.today()+timedelta(days=30)).isoformat()
    item=Opportunity(title='Current Scholarship',organization='X',opportunity_type='SCHOLARSHIP',deadline=d,description='Applications open')
    ok,_=availability_reason(item)
    assert ok


class FakeItem:
    def __init__(self, title, description='', url='https://example.com'):
        self.title=title; self.description=description; self.application_url=url; self.source_url=url; self.source_name='Web'; self.metadata={}; self.deadline=''; self.opportunity_type='SCHOLARSHIP'

def test_collection_is_not_actionable():
    from intelligence.opportunity_quality import classify_page
    assert classify_page(FakeItem('16 Masters Scholarships in Data Science and AI', 'A list of open scholarships')) == 'collection'

def test_actionable_page_is_opportunity():
    from intelligence.opportunity_quality import classify_page
    assert classify_page(FakeItem('AI Scholarship 2027', 'Applications are open. Apply now before the application deadline.')) == 'opportunity'

def test_deadline_context_beats_unrelated_future_year():
    from intelligence.freshness import availability_reason
    item=FakeItem('Current scholarship', 'Program launched in 2020. Application deadline: January 31, 2027. Funding review in 2028.')
    ok, reason=availability_reason(item)
    assert ok and '2027-01-31' in reason
