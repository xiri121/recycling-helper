import json

import streamlit as st

from engine import CATEGORY_LABELS, classify, get_sources


st.set_page_config(page_title="Recycling Helper", page_icon="♻️", layout="centered")
st.title("♻️ Recycling Helper")

try:
    metadata = get_sources()
except (OSError, ValueError, KeyError, json.JSONDecodeError):
    st.error("The source information is unavailable. Please consult your local official sorting guide.")
    st.stop()

source = metadata["sources"]["SH2024"]
st.caption(
    f"{metadata['region']} | Dataset v{metadata['dataset_version']} | "
    f"Source reviewed: {metadata['reviewed_on']}"
)
st.write("Enter an item, a keyword, or a short English sentence.")
st.info(
    "Guidance uses Shanghai's four-category system: recyclables, hazardous waste, wet waste, and dry waste. "
    "Hazardous and unlisted items receive no sorting advice. Uncertain matches need your confirmation."
)

with st.form("item_lookup", clear_on_submit=False):
    item = st.text_input(
        "What would you like to sort?",
        placeholder="For example: How should I recycle an empty milk carton?",
        max_chars=1000,
    )
    submitted = st.form_submit_button("Look up item", type="primary", use_container_width=True)

if submitted:
    st.session_state["lookup_query"] = item
    st.session_state.pop("lookup_result", None)
    try:
        st.session_state["lookup_result"] = classify(item)
    except (OSError, ValueError, KeyError):
        st.error("The dataset is unavailable or invalid. Please consult the official guide instead.")

result = st.session_state.get("lookup_result")
if result is not None:
    if result.status == "classified":
        st.success(f"**{result.item}**: {CATEGORY_LABELS[result.category]}")
        st.write(result.advice)
        if result.match_type == "sentence":
            st.caption(f"Item recognized in your sentence: {result.matched_alias}")
    elif result.status == "refuse":
        st.error(result.advice)
    else:
        st.warning(result.advice)

    if result.candidates:
        st.write("Choose only if this is the exact item you mean:")
        for index, candidate in enumerate(result.candidates):
            if st.button(candidate, key=f"candidate_{index}_{candidate}"):
                try:
                    st.session_state["lookup_result"] = classify(candidate)
                    st.session_state["lookup_query"] = candidate
                    st.rerun()
                except (OSError, ValueError, KeyError):
                    st.session_state.pop("lookup_result", None)
                    st.error("The dataset is unavailable. Please consult the official guide instead.")

    st.link_button("Read Shanghai's official sorting guide", result.source_url or source["url"])

with st.expander("Examples you can try"):
    st.write("• `How do I recycle an empty glass bottle?` — single-item sentence")
    st.write("• `bottle` — choose a more specific item")
    st.write("• `newspapr` — confirm a possible spelling match")
    st.write("• `I have a battery and a newspaper` — hazardous-item refusal takes priority")

with st.expander("Official source and local collection conditions"):
    st.write("Shanghai Household Waste Sorting Guide (2024 edition), issued by the Shanghai Landscaping and City Appearance Administrative Bureau.")
    st.write(
        "The dataset is a curated subset of the official list. English names and aliases are app translations. "
        "Disposable paper cups, plastic cups, and takeaway containers can require district-specific recovery schemes. "
        "Check the collection notices for your district or building."
    )
    st.write(
        "Hazardous-item screening is deliberately conservative, including all battery mentions and possible hazard misspellings. "
        "It does not assign an official hazard category to every flagged item."
    )
    st.link_button("Open the official source", source["url"])
