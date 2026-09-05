export const meta = {
  name: 'source-total-elapsed',
  description: 'Find open-license whole-step total-elapsed (incl. workup) times for two benign preps; adversarially verify each',
  phases: [{ title: 'Find' }, { title: 'Verify' }],
}

const FIND_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          reaction: { type: 'string', description: 'A or B' },
          value_minutes: { type: 'number' },
          raw_value: { type: 'string', description: 'the value as stated in the source, with unit' },
          source_url: { type: 'string' },
          source_name: { type: 'string' },
          license: { type: 'string' },
          exact_quote: { type: 'string', description: 'the exact sentence(s) stating the timing' },
          is_total_including_workup: { type: 'boolean' },
          notes: { type: 'string' },
        },
        required: ['reaction', 'source_url', 'exact_quote', 'is_total_including_workup'],
      },
    },
  },
  required: ['findings'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['CONFIRM', 'REJECT'] },
    reason: { type: 'string' },
    confirmed_value_minutes: { type: 'number' },
    confirmed_is_total: { type: 'boolean' },
  },
  required: ['verdict', 'reason'],
}

const REACTIONS = [
  'Two target benign organic preparations. For EACH we need the WHOLE-PROCESS TOTAL ELAPSED wall-clock time',
  'from the start of the procedure to the finished, dried, purified product -- INCLUDING workup',
  '(quench, filtration, washing, extraction, distillation, recrystallization, and DRYING time).',
  'NOT just the reaction/reflux time. If a source gives only the reaction step time and leaves workup/drying',
  'untimed, that is NOT a total elapsed -- report is_total_including_workup=false and say so.',
  '',
  'Reaction A: Paracetamol (acetaminophen) by ACETYLATION of 4-aminophenol with ACETIC ANHYDRIDE',
  '  (typically in warm water), then filtration, washing, and drying / recrystallization.',
  'Reaction B: Isopentyl acetate (isoamyl acetate, "banana oil") by FISCHER ESTERIFICATION of isopentyl',
  '  (isoamyl) alcohol with glacial ACETIC ACID, conc. H2SO4 catalyst, under REFLUX, then aq. bicarbonate',
  '  wash, drying, and DISTILLATION.',
].join('\n')

const SOURCE_FAMILIES = [
  { key: 'libretexts', prompt: 'Search chem.libretexts.org (LibreTexts, CC BY-NC-SA) organic chemistry lab manuals and experiments.' },
  { key: 'orgsyn', prompt: 'Search Organic Syntheses (orgsyn.org) -- free peer-reviewed DETAILED prep procedures that state times and workup steps explicitly. Best bet for a real total.' },
  { key: 'oer-labmanuals', prompt: 'Search open educational resource (OER) organic-chem LAB MANUALS from universities/community colleges (pressbooks.pub, oercommons.org, .edu OER, milne open textbooks) -- often CC-BY.' },
  { key: 'wiki', prompt: 'Search Wikipedia / Wikibooks / Wikiversity (CC BY-SA) for these preparations and any stated procedure timings.' },
  { key: 'pubchem-nist', prompt: 'Search PubChem, NIST WebBook, and freely-abstracted primary literature for any stated total preparation time.' },
]

phase('Find')
const perFamily = await pipeline(
  SOURCE_FAMILIES,
  (fam) => agent(
    'You are sourcing REAL, open-license process data for a chemistry compiler. ' + REACTIONS
    + '\n\nYOUR ASSIGNED SOURCE FAMILY: ' + fam.prompt
    + '\n\nUse WebSearch and WebFetch. Find the whole-process TOTAL ELAPSED time (incl. workup + drying) for Reaction A and/or B.'
    + '\nReport ONLY what a real, fetchable, open-license page actually states. Quote the EXACT sentence(s) carrying the timing.'
    + '\nIf a source only times the reaction step (not workup/drying), still report it with is_total_including_workup=false.'
    + '\nNEVER invent a number, a URL, or a license. Finding nothing sound and returning an empty findings list is a valid, valuable result -- do that rather than guess.',
    { label: 'find:' + fam.key, phase: 'Find', agentType: 'general-purpose', schema: FIND_SCHEMA },
  ),
  (found, fam) => {
    const items = (found && found.findings) ? found.findings : []
    if (!items.length) return []
    return parallel(items.map((f) => () =>
      agent(
        'Adversarially VERIFY this sourced process-timing claim. Default to REJECT if anything is off.\n'
        + 'Claim: ' + JSON.stringify(f)
        + '\n\nUse WebFetch to OPEN the cited URL yourself. Confirm ALL of:\n'
        + '1) The URL is real, fetchable, and is the source claimed.\n'
        + '2) The license is genuinely open (name it) and permits reusing the fact.\n'
        + '3) The EXACT quoted sentence actually appears on the page and states the timing claimed.\n'
        + '4) The value is a WHOLE-PROCESS TOTAL ELAPSED incl. workup + drying -- NOT just reaction/reflux time relabeled as a total.\n'
        + '5) The number and unit are transcribed correctly (give confirmed_value_minutes).\n'
        + 'If ANY check fails, verdict=REJECT with the specific reason. A partial time mislabeled as a total is a REJECT.',
        { label: 'verify:' + fam.key, phase: 'Verify', agentType: 'general-purpose', schema: VERIFY_SCHEMA },
      ).then((v) => ({ finding: f, verdict: v }))
    ))
  },
)

const flat = perFamily.flat().filter(Boolean)
const confirmed = flat.filter((r) => r && r.verdict && r.verdict.verdict === 'CONFIRM')
const confirmedTotals = confirmed.filter((r) => r.verdict.confirmed_is_total === true)
return {
  families: SOURCE_FAMILIES.length,
  found_count: flat.length,
  confirmed_count: confirmed.length,
  confirmed_total_elapsed_count: confirmedTotals.length,
  confirmed,
  all: flat,
}
