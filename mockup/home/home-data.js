// The Human Project · homepage content.
// Static workspace content (projects in setup, team, activity). Numbers for the live San Francisco
// project and its scenarios are NOT here: index.html reads them from the engine (/world, /baseline,
// /scenario). Cities other than SF are in setup and deliberately carry no results.
window.HOME_DATA = (() => {
  const people = {
    max: { name: 'Max', initials: 'MT', role: 'Owner', color: '#3b9cff' },
    aziz: { name: 'Aziz', initials: 'AZ', role: 'Transport modeler', color: '#b46cff' },
    jk: { name: 'J.K.', initials: 'JK', role: 'Urban designer', color: '#ffad1f' },
    rm: { name: 'R.M.', initials: 'RM', role: 'Economist', color: '#4fdc7a' },
    st: { name: 'S.T.', initials: 'ST', role: 'Community liaison', color: '#ff4fa3' },
    lp: { name: 'L.P.', initials: 'LP', role: 'Transit analyst', color: '#27c4ff' },
    dw: { name: 'D.W.', initials: 'DW', role: 'Data engineer', color: '#ffd23a' },
  };

  // status: live | ingest | calibrating | draft
  const projects = {
    sf: { id: 'sf', city: 'San Francisco', area: 'FiDi & SoMa', status: 'live', thumb: 'thumbs/sf.svg', live: true,
      edited: 'Edited 4 min ago by Max' },
    oak: { id: 'oak', city: 'Oakland', area: 'Downtown', status: 'ingest', progress: 0.62, thumb: 'thumbs/oakland.svg',
      step: 'Ingesting OSM + census', detail: 'Street graph done · LODES block joins running', edited: 'Started 2 h ago by D.W.' },
    nyc: { id: 'nyc', city: 'New York', area: 'Lower Manhattan', status: 'calibrating', progress: 0.4, thumb: 'thumbs/nyc.svg',
      step: 'Calibrating', detail: 'Fitting mode split to ACS journey-to-work · pass 2 of 5', edited: 'Started yesterday by Aziz' },
    bcn: { id: 'bcn', city: 'Barcelona', area: 'Eixample', status: 'draft', thumb: 'thumbs/barcelona.svg',
      step: 'Draft', detail: 'Study area drawn · no data requested yet', edited: 'Created Oct 12 by Max' },
    ber: { id: 'ber', city: 'Berlin', area: 'Mitte', status: 'draft', thumb: 'thumbs/berlin.svg',
      step: 'Draft', detail: 'Study area drawn · waiting on data-sharing agreement', edited: 'Created Oct 3 by Max' },
  };

  // Scenarios with `engine` are computed live against the SF engine when the page loads.
  const sc = {
    hero: { name: '2nd St car-free', project: 'sf', author: 'max', status: 'Shared', edited: '4 min ago',
      engine: 'hero', fallback: { value: 9.85e6 } },
    bay: { name: 'Bay Bridge AM charge', project: 'sf', author: 'aziz', status: 'In review', edited: '1 h ago',
      engine: { policies: [{ kind: 'congestion_charge', target: 'i80', amount: 5 }] } },
    mkt: { name: 'Market St reopen (pre-2020)', project: 'sf', author: 'jk', status: 'Draft', edited: 'Yesterday',
      engine: 'market' },
    howard: { name: 'Howard St protected bike lane', project: 'sf', author: 'rm', status: 'Draft', edited: 'Oct 21', note: 'Not run yet' },
    bart: { name: 'Embarcadero BART · 4-min headways', project: 'sf', author: 'lp', status: 'Draft', edited: 'Oct 20', note: 'Needs transit supply edits' },
    broadway: { name: 'Broadway busway', project: 'nyc', author: 'aziz', status: 'Blocked', edited: 'Oct 22', note: 'Waiting for calibration' },
    superblock: { name: 'Superilla pilot · Consell de Cent', project: 'bcn', author: 'max', status: 'Draft', edited: 'Oct 12', note: 'Project in draft' },
  };

  const workspaces = [
    { id: 'sfp', name: 'SF Planning · Downtown', short: 'SF', color: '#3b9cff', plan: 'Team · 5 seats',
      projects: ['sf', 'oak', 'nyc', 'bcn'], scenarios: ['hero', 'bay', 'mkt', 'howard', 'broadway'],
      team: ['max', 'aziz', 'jk', 'rm', 'st'],
      activity: [
        { who: 'max', what: 'shared', target: '2nd St car-free', extra: 'with SFMTA reviewers', t: '4m' },
        { who: 'aziz', what: 'ran', target: 'Bay Bridge AM charge', extra: '$5 at the I-80 inlet', t: '1h' },
        { who: 'jk', what: 'commented on', target: 'Market St reopen (pre-2020)', extra: '“check the forced turns at 3rd”', t: '3h' },
        { who: null, what: 'Engine recalibrated', target: 'San Francisco', extra: 'mode split vs ACS 19–23', t: '5h' },
        { who: 'dw', what: 'started ingest for', target: 'Oakland · Downtown', extra: '', t: '2h' },
        { who: 'rm', what: 'created', target: 'Howard St protected bike lane', extra: '', t: '3d' },
      ] },
    { id: 'btl', name: 'Bay Area Transit Lab', short: 'BT', color: '#4fdc7a', plan: 'Team · 4 seats',
      projects: ['sf', 'oak'], scenarios: ['bay', 'bart', 'mkt'],
      team: ['aziz', 'lp', 'dw', 'max'],
      activity: [
        { who: 'lp', what: 'drafted', target: 'Embarcadero BART · 4-min headways', extra: '', t: '4d' },
        { who: 'aziz', what: 'ran', target: 'Bay Bridge AM charge', extra: '$5 at the I-80 inlet', t: '1h' },
        { who: 'dw', what: 'refreshed', target: 'BART ridership', extra: 'Sep 2026 exits', t: '6d' },
        { who: null, what: 'Ingest 62%', target: 'Oakland · Downtown', extra: 'census block joins', t: '12m' },
      ] },
    { id: 'me', name: 'Personal', short: 'M', color: '#ffad1f', plan: 'Free',
      projects: ['bcn', 'ber'], scenarios: ['superblock'],
      team: ['max'],
      activity: [
        { who: 'max', what: 'created', target: 'Barcelona · Eixample', extra: '', t: '12d' },
        { who: 'max', what: 'drew the study area for', target: 'Berlin · Mitte', extra: '', t: '3w' },
      ] },
  ];

  // Freshness of the inputs the SF engine is built from. `flag` = key in GET /health → data.
  const sources = [
    { name: 'OpenStreetMap', what: 'Streets, buildings, POIs', fresh: 'Oct 22, 2026', flag: null },
    { name: 'LODES 2023', what: 'Where people work and live', fresh: 'Release 8.3', flag: 'lodes' },
    { name: 'ACS 2019–23', what: 'Journey to work, income', fresh: '5-year', flag: 'acs' },
    { name: 'DataSF', what: 'Land use, traffic counts', fresh: 'Oct 20, 2026', flag: 'landuse', flag2: 'traffic_counts' },
    { name: 'BART', what: 'Station exits by hour', fresh: 'Sep 2026', flag: 'transit' },
    { name: 'Google Places', what: 'Businesses, popular times', fresh: 'Oct 23, 2026', flag: 'businesses' },
  ];

  // Calibration targets: commute mode split from ACS 2019–23 journey-to-work, study-area workers (%).
  const calibration = { car: 34.4, transit: 48.4, walk: 12.9, bike: 4.3 };
  // Shown only if the engine can't be reached (last calibrated run).
  const calibrationFallback = { car: 35.1, transit: 49.7, walk: 11.1, bike: 4.2 };

  const notifications = [
    { who: 'jk', text: 'J.K. commented on Market St reopen (pre-2020)', t: '3h' },
    { who: 'aziz', text: 'Aziz requested your review on Bay Bridge AM charge', t: '1h' },
    { who: null, text: 'Oakland · Downtown ingest passed 60%', t: '12m' },
  ];

  return { people, projects, scenarios: sc, workspaces, sources, calibration, calibrationFallback, notifications, me: 'max' };
})();
