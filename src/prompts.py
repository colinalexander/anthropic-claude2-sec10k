template = """\
Below are the key sections from a company's 10-K filing, along with the MDA section \
for each of the two prior years.

Management's Discussion and Analysis:
<mda>{mda}</mda>

Prior Year's MDA:
<prior_mda>{prior_mda}</mda>

MDA Two Years Ago:
<prior_prior_mda>{prior_prior_mda}</prior_prior_mda>

Business:
<biz>{biz}</biz>

Risk Factors:
<risk_factors>{risk_factors}</risk_factors>

Legal Proceedings:
<legal>{legal}</legal>

Accounting Policies and Estimates:
<accounting>{accounting}</accounting>

Summarize each of the above sections from this company's 10-K filing using a bullet \
point format. 
For the first three sections (Business, Risk Factors and MDA), summarize in about ten \
bullet points for each of these sections. \
For the remaining two sections (legal and accounting), summarize in 2-4 bullet points \
each. 
For all five sections, provide a sentiment score between -1.0 and +1.0 for the overall \
tone of that section. 
Focus on the key points and overall tone.

Do not summarize either of the prior years MDA sections.  Rather, create a new section \
called "Change in Business Over Prior Two Years". \
In this section, analyze the change of the business over time.  \
Provide 8-12 bullet points for this analysis.

The sentiment score should be a continuous value between -1.00 and 1.00 reflecting \
the overall sentiment of that section.  For the sentiment scores, use:

Positive (0.82) for a positive tone
Negative (-0.73) for a negative/cautious tone
Neutral (0.02) for a balanced/informational tone

Provide an objective summary and sentiment assessment based on the content provided.
Do not make up any information if you do not know it or are unable to summarize.

Precede the above information with an executive summary.

Just provide the requested information in markdown format \
(use Level 3 headings for each section). Do not add extra content.
"""
