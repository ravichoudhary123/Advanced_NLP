from datetime import datetime, timedelta

from enterprise_search import ACL, ActivityEvent, Document, EnterpriseSearchService, UserContext
from enterprise_search.models import Intent

NOW = datetime(2026, 5, 6, 12, 0, 0)


def make_service():
    docs = [
        Document(
            doc_id="abs-onboarding",
            title="ABS Onboarding Guide",
            body="Steps for ABS onboarding include SSO setup, repository access, and SharePoint training.",
            source="confluence",
            url="https://example.test/confluence/abs-onboarding",
            acl=ACL(allow_groups=frozenset({"engineering"})),
            owner_team="platform",
            department="technology",
            doc_type="guide",
            tags=("ABS", "onboarding"),
            updated_at=NOW - timedelta(days=10),
            popularity=0.8,
            source_authority=0.9,
            aliases=("ABS onboarding",),
        ),
        Document(
            doc_id="milvus-incident",
            title="Milvus Latency Issue RCA",
            body="Last week the Milvus latency issue was traced to compaction pressure and fixed by segment tuning.",
            source="slack",
            url="https://example.test/slack/milvus-latency",
            acl=ACL(allow_groups=frozenset({"engineering", "sre"})),
            owner_team="search-platform",
            doc_type="incident",
            updated_at=NOW - timedelta(days=3),
            popularity=0.6,
            source_authority=0.7,
        ),
        Document(
            doc_id="fnol-process",
            title="Latest Claims FNOL Process",
            body="The latest claims First Notice of Loss process requires intake validation and adjuster assignment.",
            source="sharepoint",
            url="https://example.test/sharepoint/fnol",
            acl=ACL(allow_groups=frozenset({"claims"})),
            business_unit="claims",
            doc_type="process",
            tags=("FNOL", "claims"),
            updated_at=NOW - timedelta(days=1),
            popularity=0.7,
            source_authority=1.0,
            aliases=("FNOL process", "First Notice of Loss"),
        ),
        Document(
            doc_id="irs-dashboard",
            title="IRS Dashboard",
            body="Dashboard for incident response scorecards, operational readiness, and executive metrics.",
            source="ado",
            url="https://example.test/ado/irs-dashboard",
            acl=ACL(allow_groups=frozenset({"leadership"})),
            doc_type="dashboard",
            updated_at=NOW - timedelta(days=14),
            aliases=("IRS dashboard",),
        ),
    ]
    events = [
        ActivityEvent(
            event_id="evt-1",
            doc_id="milvus-incident",
            event_type="updated",
            event_time=NOW - timedelta(days=2),
            activity_text="Milvus latency issue updated with mitigation last week",
        ),
        ActivityEvent(
            event_id="evt-2",
            doc_id="fnol-process",
            event_type="updated",
            event_time=NOW - timedelta(days=1),
            activity_text="Latest claims FNOL process approved",
        ),
    ]
    return EnterpriseSearchService(docs, events, now=NOW)


def test_exact_title_lookup_promotes_title_match():
    response = make_service().search("ABS onboarding", UserContext("u1", frozenset({"engineering"})))

    assert response.query.intent == Intent.EXACT_LOOKUP
    assert response.results[0].doc_id == "abs-onboarding"
    assert "title/entity match" in response.results[0].explanation
    assert response.answer.citations[0].doc_id == "abs-onboarding"


def test_recent_activity_query_uses_recent_route():
    response = make_service().search("Milvus latency issue last week", UserContext("sre-user", frozenset({"sre"})))

    assert response.query.intent == Intent.RECENT_ACTIVITY
    assert response.results[0].doc_id == "milvus-incident"
    assert "recent" in response.query.retrieval_plan
    assert "recent activity match" in response.results[0].explanation


def test_acronym_expansion_and_freshness_for_fnol():
    response = make_service().search("latest claims FNOL process", UserContext("claims-user", frozenset({"claims"})))

    assert response.query.intent == Intent.FRESH_LOOKUP
    assert "first notice of loss" in response.query.normalized_query
    assert response.results[0].doc_id == "fnol-process"
    assert not response.answer.no_answer


def test_permission_filtering_is_fail_closed():
    response = make_service().search("IRS dashboard", UserContext("engineer", frozenset({"engineering"})))

    assert all(result.doc_id != "irs-dashboard" for result in response.results)
    assert response.trace["permissioned_candidates"] == 0
    assert response.answer.no_answer


def test_metadata_source_filter_and_facets():
    response = make_service().search("source:sharepoint claims process", UserContext("claims-user", frozenset({"claims"})))

    assert response.query.source_preference == "sharepoint"
    assert response.results[0].source == "sharepoint"
    assert response.facets["source"] == {"sharepoint": 1}
