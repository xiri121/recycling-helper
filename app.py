import streamlit as st
from engine import classify

st.set_page_config(page_title="Recycling Helper", page_icon="♻️", layout="centered")

st.title("♻️ Recycling Helper")
st.caption("Rule Version: v1.0 (Last updated: 2026-10-24) | Always defer to local building management notices.")
st.caption("Enter an item to see guidance from the current dataset.")

st.info(
    "This helper only provides guidance for ordinary items explicitly listed in its dataset. "
    "It will not guess how to sort hazardous or unlisted items. Rules vary by location; follow your local authority's guidance."
)

with st.form("item_lookup", clear_on_submit=False):
    item = st.text_input("Item name", placeholder="For example: newspaper, plastic drink bottle")
    submitted = st.form_submit_button("Look up item", type="primary", use_container_width=True)

if submitted:
    result = classify(item)
    if result.status == "classified":
        st.success(f"**{result.item}**: {result.category}")
        if result.advice:
            st.write(result.advice)
        st.caption("This result comes from the current dataset. Follow your local disposal rules.")
    elif result.status == "refuse":
        st.error(result.advice)
    elif result.status == "clarify":
        st.warning(result.advice)
    else: # unknown
        st.warning(result.advice)

with st.expander("Data and guidance"):
    st.write(
        "Classification guidance comes from data_rules.csv. Hazardous-item keywords and names that need clarification "
        "are maintained in data_refuse.csv and data_clarify.csv. This starter dataset is not a complete catalog for every location."
    )
