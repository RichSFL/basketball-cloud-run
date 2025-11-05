const express = require('express');
const fetch = require('node-fetch');
const app = express();

// ==================== CONFIG ====================
const API_TOKEN = '232427-K2VL8Pj81T3rFy';
const LEAGUE_ID = '25067';
const SPORT_ID = '18';

const QUARTER_SECONDS = 300;
const OT_SECONDS = 180;
const GAME_SECONDS = 1200;

const GAME_SLOTS = {
  gameA: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1431967045955747941/AI09hC285IkvfUR8G9xF8ZhwDf7Pl93KLHI0QYXTL8J0Z3MZAxuUCdOgcWpTM27Gu5Xs",
      "https://discord.com/api/webhooks/1430963075384606821/CCcJJ6KuJL5viHQ-jNSy8D2PgLHxS5DRjZ74d3IEQ8ClqwkO3HfMUGH6Tt5Z9mqzNjts"
    ]
  },
  gameB: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1432030484577255618/jleglfSYnTNMyh3BcBZ4As_WJFRDtn37JepKPltsp0ar3jqrCgPk_THnDYVvWwBrtpWe",
      "https://discord.com/api/webhooks/1431600519041781760/Zbbz0r6NGOG-9Pm1qMriVKAeHLeWEmQTelm0a55byZ9xbVIXbQjhPE-np8CxBzO9UTJG"
    ]
  },
  gameC: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1430662256676442112/95PwH5E-yDxqxu_sHGikRnqLvVSeqI5FoxYNS-TGXaKiEcLpCJpR_HZ_6__AR1WUQhID",
      "https://discord.com/api/webhooks/1431013136055533769/gjr_VcpXRN7ei8js0BtuP-orw6qwIr-zeyLHYXMm0yfblutalBpUbMmFwa1T1T_4U-3a"
    ]
  },
  gameD: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1431600103616942081/6fPGAtsmpELGt4Cz8Xr_exa6_H0J9EYkZbSkWeH4rJdVgcOdtrOkr--OS9Ouyj-s89zc",
      "https://discord.com/api/webhooks/1429140091711914085/6ZGa0lWJ8PgIf-Z4Chvam1ID6_2GY41CnB7JDU4QJH2PtgLeN4z1VYthprH6FmWI5AHq"
    ]
  },
  gameE: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1431002593106071765/JfdaKjRpfw_jAMXo56C0aoDYvyGQJQf8MBvx2Ot9JTJMIUVvWd3hm1dCeREiIttzydQt",
      "https://discord.com/api/webhooks/1429137447807094896/8Db_IO_hLRRYNEBtmFnOuky9QbIZd52V0iQwTt0w-bgaB3EDXB72U63exwzJjMP9GW6q"
    ]
  },
  gameF: { 
    enabled: true, 
    webhooks: [
      "https://discord.com/api/webhooks/1431610966432288840/csJ1l_hGEz8_Aq-6-jkiAARN06e2s4UtIrkEXD-BzyM49g_9uBNM1Yw4PC01m3b40SoX",
      "https://discord.com/api/webhooks/1431610266256281756/ZwWLP7rTvZaNMbiTTiwA078JmHShvbsWaeXOCW0pKMrQPtzQeZhm3Z4y9ce7DpC2yXH5"
    ]
  }
};

const ALERT_THRESHOLD_POINTS = 5;
const ALERT_MIN_INTERVAL_MS = 30 * 1000;
const LEADER_THRESHOLD_POINTS = 5;

// In-memory state (replace with Redis/Database for production)
const gameState = {};
const trackedGames = {};

// ==================== HELPERS ====================
function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

function avg(arr) {
  return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
}

const { Storage } = require('@google-cloud/storage');
const storage = new Storage();
const bucket = storage.bucket('basketball-samples');

async function logSamplesToCSV(eventId, game, state, q, m, s, played, homeScore, awayScore, totalScore) {
  try {
    const homePPS = homeScore / played;
    const awayPPS = awayScore / played;
    const totalPPS = totalScore / played;
    
    const homeRaw = +(homePPS * GAME_SECONDS).toFixed(4);
    const homeAvg = +((avg(state.homeSamples)) * GAME_SECONDS).toFixed(4);
    const awayRaw = +(awayPPS * GAME_SECONDS).toFixed(4);
    const awayAvg = +((avg(state.awaySamples)) * GAME_SECONDS).toFixed(4);
    const totalRaw = +(totalPPS * GAME_SECONDS).toFixed(4);
    const totalAvg = +((avg(state.totalSamples)) * GAME_SECONDS).toFixed(4);
    
    const row = `${new Date().toISOString()},${eventId},"${game.home.name}","${game.away.name}",${q},${m}:${s},${played},${homeScore},${awayScore},${totalScore},${homePPS.toFixed(6)},${awayPPS.toFixed(6)},${totalPPS.toFixed(6)},${homeRaw},${homeAvg},${awayRaw},${awayAvg},${totalRaw},${totalAvg},${state.homeSamples.length},${state.awaySamples.length},${state.totalSamples.length}\n`;
    
    const filename = `samples_${eventId}.csv`;
    const file = bucket.file(filename);
    
    try {
      const [exists] = await file.exists();
      if (!exists) {
        const header = `timestamp,eventId,homeName,awayName,quarter,timeRemaining,playedSeconds,homeScore,awayScore,totalScore,homePPS,awayPPS,totalPPS,homeRaw,homeAvg,awayRaw,awayAvg,totalRaw,totalAvg,homeSampleCount,awaySampleCount,totalSampleCount\n`;
        await file.save(header);
        log(`✅ Created samples CSV in GCS: gs://basketball-samples/${filename}`);
      }
      await file.append(row);
    } catch (e) {
      log(`❌ GCS error: ${e.message}`);
    }
  } catch (err) {
    log(`⚠️ Error logging samples: ${err.message}`);
  }
}


function toInt(v) {
  return parseInt(v, 10);
}

function getCurrentEDTTime() {
  return new Date().toLocaleString("en-US", { timeZone: "America/New_York" });
}

function extractGamerName(fullTeamName) {
  const match = fullTeamName.match(/\(([^)]+)\)$/);
  return match ? match[1] : fullTeamName;
}

function calculatePlayedTime(q, m, s) {
  if (q <= 4) {
    return ((q - 1) * QUARTER_SECONDS) + (QUARTER_SECONDS - (m * 60 + s));
  } else {
    const regulationTime = 4 * QUARTER_SECONDS;
    const overtimePeriods = q - 4;
    const completedOTs = (overtimePeriods - 1) * OT_SECONDS;
    const currentOT = OT_SECONDS - (m * 60 + s);
    return regulationTime + completedOTs + currentOT;
  }
}

function analyzeMomentum(samples) {
  if (!samples || samples.length < 5) return "INSUFFICIENT_DATA";
  
  const last5 = samples.slice(-5);
  const diffs = [];
  for (let i = 1; i < last5.length; i++) {
    diffs.push(last5[i] - last5[i - 1]);
  }
  
  const ups = diffs.filter(d => d > 0.0005).length;
  const downs = diffs.filter(d => d < -0.0005).length;
  
  if (ups >= 3) return "ON_FIRE";
  if (downs >= 3) return "COOLING_OFF";
  if (ups === downs) return "STEADY_PACE";
  if (ups > downs) return "HEATING_UP";
  return "SLOWING_DOWN";
}

function formatMomentumForDiscord(momentum) {
  const map = {
    "ON_FIRE": "🔥 ON FIRE!!",
    "HEATING_UP": "⚡ HEATING UP",
    "COOLING_OFF": "❄️ COOLING OFF",
    "SLOWING_DOWN": "📉 SLOWING DOWN",
    "STEADY_PACE": "➡️ STEADY PACE",
    "INSUFFICIENT_DATA": "📊 INSUFFICIENT DATA"
  };
  return map[momentum] || momentum;
}

function classifyPaceTrend(pps) {
  if (!pps || pps.length < 5) return "Not enough data";
  
  const last = pps.slice(-5);
  const diffs = last.slice(1).map((v, i) => v - last[i]);
  const ups = diffs.filter(d => d > 0).length;
  const downs = diffs.filter(d => d < 0).length;
  
  if (Math.max(...last) - Math.min(...last) <= 0.002) return "RELIABLE - Rock Solid";
  if (ups === 4) return "STRONG - Heating Up";
  if (downs === 4) return "CAUTION - Cooling Down";
  
  let turns = 0;
  for (let i = 0; i < diffs.length - 1; i++) {
    if (Math.sign(diffs[i]) !== Math.sign(diffs[i + 1]) && diffs[i] !== 0 && diffs[i + 1] !== 0) turns++;
  }
  
  if (turns >= 2) return "RISKY - Unpredictable";
  
  return ups > downs ? "STRONG - Heating Up" : "CAUTION - Cooling Down";
}

function formatPaceTrendForDiscord(p) {
  if (p.includes("STRONG")) return "✅ **STRONG**";
  if (p.includes("RELIABLE")) return "✅ **RELIABLE**";
  if (p.includes("CAUTION")) return "⚠️ **CAUTION**";
  if (p.includes("RISKY")) return "❌ **RISKY**";
  return p;
}

function calculateTeamTotals(gameTotal, spread) {
  const T = gameTotal;
  const S = Math.abs(spread);
  
  let TT_high = (T + S) / 2;
  let TT_low = T - TT_high;
  
  const highDecimal = TT_high % 1;
  const lowDecimal = TT_low % 1;
  
  if (highDecimal === 0.5 && lowDecimal === 0.5) {
    return { high: TT_high, low: TT_low };
  }
  
  if (highDecimal === 0 && lowDecimal === 0) {
    TT_high -= 0.5;
    TT_low -= 0.5;
    return { high: TT_high, low: TT_low };
  }
  
  TT_high = Math.round(TT_high * 2) / 2;
  TT_low = Math.round(TT_low * 2) / 2;
  
  return { high: TT_high, low: TT_low };
}

function isAccelerating(samples) {
  if (!samples || samples.length < 5) return false;
  
  const last5 = samples.slice(-5);
  const diffs = [];
  for (let i = 1; i < last5.length; i++) {
    diffs.push(last5[i] - last5[i - 1]);
  }
  
  const ups = diffs.filter(d => d > 0.0005).length;
  return ups >= 3;
}

function isLeaderOnFire(samples) {
  return analyzeMomentum(samples) === "ON_FIRE";
}

// ==================== ODDS FETCHING ====================
async function getOddsWithFallback(eventId) {
  let info = await fetchAndExtractOddsV1(`https://api.b365api.com/v1/event/odds?token=${API_TOKEN}&event_id=${eventId}`);
  if (info) return info;
  
  info = await fetchAndExtractOddsV2(`https://api.b365api.com/v2/event/odds?token=${API_TOKEN}&event_id=${eventId}&odds_market=3`);
  if (info) return info;
  
  info = await fetchAndExtractOddsV2(`https://api.b365api.com/v2/event/odds?token=${API_TOKEN}&event_id=${eventId}`);
  if (info) return info;
  
  info = await fetchAndExtractOddsV2(`https://api.b365api.com/v2/event/odds/summary?token=${API_TOKEN}&event_id=${eventId}`);
  if (info) return info;
  
  return null;
}

async function fetchAndExtractOddsV1(url) {
  try {
    const res = await fetch(url);
    const json = await res.json();
    if (json.success === 1 && json.results) return normalizeOdds(json.results);
  } catch (e) {
    log(`Odds V1 error: ${e.message}`);
  }
  return null;
}

async function fetchAndExtractOddsV2(url) {
  try {
    const res = await fetch(url);
    const json = await res.json();
    if (json.success === 1 && json.results) return normalizeOdds(json.results);
  } catch (e) {
    log(`Odds V2 error: ${e.message}`);
  }
  return null;
}

function normalizeOdds(results) {
  const markets = Array.isArray(results) ? results : [results];
  
  let totalLine = null, overOdds = '', underOdds = '', sourceMarket = '';
  let spread = null, homeSpreadOdds = '', awaySpreadOdds = '';
  
  const totalPriority = ['18_3', '18_9', '18_6'];
  for (const entry of markets) {
    for (const key of totalPriority) {
      const arr = entry[key];
      if (arr && Array.isArray(arr) && arr.length > 0) {
        const m = arr[0];
        
        const line =
          (typeof m.total === 'number' && isFinite(m.total)) ? m.total :
          (!isNaN(parseFloat(m.total))) ? parseFloat(m.total) :
          (typeof m.handicap === 'number' && isFinite(m.handicap)) ? m.handicap :
          (!isNaN(parseFloat(m.handicap))) ? parseFloat(m.handicap) :
          null;
        
        if (line !== null) {
          totalLine = line;
          overOdds = m.over_od || m.over_odds || m.o || '';
          underOdds = m.under_od || m.under_odds || m.u || '';
          sourceMarket = key;
          break;
        }
      }
    }
    if (totalLine !== null) break;
  }
  
  for (const entry of markets) {
    const arr = entry['18_2'];
    if (arr && Array.isArray(arr) && arr.length > 0) {
      const m = arr[0];
      
      const spreadVal =
        (typeof m.handicap === 'number' && isFinite(m.handicap)) ? m.handicap :
        (!isNaN(parseFloat(m.handicap))) ? parseFloat(m.handicap) :
        (typeof m.total === 'number' && isFinite(m.total)) ? m.total :
        (!isNaN(parseFloat(m.total))) ? parseFloat(m.total) :
        null;
      
      if (spreadVal !== null) {
        spread = spreadVal;
        homeSpreadOdds = m.home_od || m.home_odds || m.h || '';
        awaySpreadOdds = m.away_od || m.away_odds || m.a || '';
        break;
      }
    }
  }
  
  if (totalLine === null) return null;
  
  return { 
    totalLine, 
    overOdds, 
    underOdds, 
    sourceMarket,
    spread: spread !== null ? spread : 0,
    homeSpreadOdds,
    awaySpreadOdds
  };
}

// ==================== DISCORD SENDING ====================
async function sendAlert(message, slot) {
  const slotConfig = GAME_SLOTS[slot];
  if (!slotConfig) return;
  
  for (const webhookUrl of slotConfig.webhooks) {
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: message })
      });
      log(`✅ Alert sent to ${slot}`);
    } catch (e) {
      log(`❌ Discord error for ${slot}: ${e.message}`);
    }
  }
}

async function sendDiscordEmbed(embed, slot) {
  const slotConfig = GAME_SLOTS[slot];
  if (!slotConfig) return;
  
  for (const webhookUrl of slotConfig.webhooks) {
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ embeds: [embed] })
      });
      log(`✅ Embed sent to ${slot}`);
    } catch (e) {
      log(`❌ Discord embed error for ${slot}: ${e.message}`);
    }
  }
}

// ==================== STATE MANAGEMENT ====================
function getGameState(eventId) {
  if (!gameState[eventId]) {
    gameState[eventId] = {
      gameId: eventId,
      homeSamples: [],
      awaySamples: [],
      totalSamples: [],
      silentMode: true,
      paceHistory: "",
      finalReportSent: false,
      lastTimestamp: "",
      lastAlert: 0,
      missedCycles: 0,
      bettingWindowFired: false,
      decisionWindowComplete: false,
      sawQ4Yet: false,
      lastHomeScore: '',
      lastAwayScore: '',
      lastTotalScore: '',
      lastHomeName: '',
      lastAwayName: '',
      lastLeaderStatus: '',
      bettingWindowProjection: null,
      bettingWindowLine: null,
      bettingWindowRecommendation: null,
      homeTeamProjection: null,
      homeTeamLine: null,
      homeTeamRec: null,
      awayTeamProjection: null,
      awayTeamLine: null,
      awayTeamRec: null,
      experimentalBlendedTotal: null,
      experimentalBlendedHome: null,
      experimentalBlendedAway: null,
      experimentalTotalLine: null,
      experimentalHomeTeamLine: null,
      experimentalAwayTeamLine: null,
      experimentalTotalRec: null,
      experimentalHomeRec: null,
      experimentalAwayRec: null
    };
  }
  return gameState[eventId];
}

// ==================== MAIN ORCHESTRATION ====================
app.post('/run-orchestration', async (req, res) => {
  log('🏀 [ORCHESTRATION] Starting Basketball Projections');
  log('📡 Fetching games from API...');
  
  try {
    const apiUrl = `https://api.b365api.com/v3/events/inplay?sport_id=${SPORT_ID}&league_id=${LEAGUE_ID}&token=${API_TOKEN}`;
    const response = await fetch(apiUrl);
    const data = await response.json();
    
    if (data.success === 1 && data.results && data.results.length > 0) {
      log(`✅ Found ${data.results.length} games`);
      await processApiData(data);
    } else {
      log('⚠️ No games found');
    }
  } catch (error) {
    log(`❌ Orchestration error: ${error.message}`);
  }
  
  res.json({ success: true });
});

async function processApiData(data) {
  const activeEventIds = data.results.map(g => g.id);
  const enabledSlots = Object.keys(GAME_SLOTS).filter(s => GAME_SLOTS[s].enabled);
  const gamesToProcess = [];

  for (const slot of enabledSlots) {
    log(`Processing slot: ${slot}`);
    
    if (trackedGames[slot]) {
      log(`Slot ${slot} already has gameId ${trackedGames[slot]}`);
      
      const gameData = data.results.find(g => g.id === trackedGames[slot]);
      
      if (gameData && gameData.ss && gameData.timer) {
        gameData.slot = slot;
        gamesToProcess.push(gameData);
        log(`✅ Added game ${gameData.id} for slot ${slot}`);
      } else if (!activeEventIds.includes(trackedGames[slot])) {
        log(`Game disappeared from API for slot ${slot}`);
        delete trackedGames[slot];
      }
    } else {
      log(`Slot ${slot} empty, searching for Q1 game`);
      
      const allTrackedIds = Object.values(trackedGames);
      const pick = data.results.find(g => {
        return (
          g.ss &&
          g.timer &&
          toInt(g.timer.q) === 1 &&
          !allTrackedIds.includes(g.id)
        );
      });

      if (pick) {
        log(`Slot ${slot} picked: ${pick.home.name} vs ${pick.away.name}`);
        trackedGames[slot] = pick.id;
        pick.slot = slot;
        pick.isNewSelection = true;
        gamesToProcess.push(pick);

        await sendAlert(
          `🟢 **Game Reserved for Tracking!** (Q1)\n\n` +
          `**${pick.home.name} vs. ${pick.away.name}** [Game ${slot.charAt(4).toUpperCase()}]\n\n` +
          `⏳ Slot locked. Waiting for Q2 to begin sampling...\n` +
          `🚨 Projection alerts will start in Q3.\n\n` +
          `━━━━━━━━━━━━━━━━━━━━━━━━`,
          slot
        );

        const playerA = extractGamerName(pick.home.name);
        const playerB = extractGamerName(pick.away.name);
        log(`Sending H2H stats for ${playerA} vs ${playerB}`);
        // H2H stats would go here (simplified for now)
      }
    }
  }

  // Deduplicate and process
  const uniqueGames = [];
  const seenIds = new Set();
  
  for (const game of gamesToProcess) {
    if (!seenIds.has(game.id)) {
      seenIds.add(game.id);
      uniqueGames.push(game);
    }
  }

  for (const game of uniqueGames) {
    log(`🎮 Processing game ${game.id} for slot ${game.slot}`);
    const oddsInfo = await getOddsWithFallback(game.id);
    await processGame(game, oddsInfo);
  }
}

async function processGame(game, oddsInfo) {
  const eventId = game.id;
  const slot = game.slot;
  let state = getGameState(eventId);

  if (state.finalReportSent) {
    log(`⏭️ Final report already sent for ${eventId}`);
    return;
  }

  const [homeScore, awayScore] = game.ss.split('-').map(Number);
  const totalScore = homeScore + awayScore;
  
  const q = toInt(game.timer.q), m = toInt(game.timer.tm), s = toInt(game.timer.ts);
  const stamp = `${q}-${m}-${s}`;

  log(`Scores: ${homeScore}-${awayScore}, Q${q}, ${m}:${s}`);

  // Skip Q1 - just track
  if (q === 1) {
    log(`Q1: Game tracked but skipping samples`);
    state.lastTimestamp = stamp;
    return;
  }

  // Stale game detection
  if (state.lastTimestamp === stamp) {
    state.missedCycles = (state.missedCycles || 0) + 1;
    log(`⚠️ No update. Missed cycles: ${state.missedCycles}`);
    
    if (state.missedCycles >= 8 && q <= 2) {
      log('❌ Game stalled - releasing slot');
      await sendAlert(`⚠️ Game stalled (Q${q}). Releasing slot.`, slot);
      delete trackedGames[slot];
      return;
    }
    return;
  } else {
    state.missedCycles = 0;
  }

  state.lastHomeScore = homeScore;
  state.lastAwayScore = awayScore;
  state.lastTotalScore = totalScore;
  state.lastHomeName = game.home.name;
  state.lastAwayName = game.away.name;

  // Skip duplicate
  if (state.lastTimestamp === stamp && state.lastHomeScore === homeScore && state.lastAwayScore === awayScore && !game.isNewSelection) {
    // Check for game end
    if (!state.finalReportSent && q === 4 && m === 0 && s === 0 && homeScore !== awayScore) {
      log('🏁 Game ended');
      state.finalReportSent = true;
      state.decisionWindowComplete = true;
      await sendAlert(
        `⏰ **${getCurrentEDTTime()}**\n\n` +
        `✅ **FINAL** [Game ${slot.charAt(4).toUpperCase()}]\n\n` +
        `**${game.home.name} vs. ${game.away.name}**\n` +
        `FINAL: ${homeScore}-${awayScore} (Total: ${totalScore})\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━`,
        slot
      );
      delete trackedGames[slot];
    }
    return;
  }

  const played = calculatePlayedTime(q, m, s);
  if (played <= 0) return;

  const homePPS = homeScore / played;
  const awayPPS = awayScore / played;
  const totalPPS = totalScore / played;

  state.homeSamples.push(homePPS);
  state.awaySamples.push(awayPPS);
  state.totalSamples.push(totalPPS);
  
  logSamplesToCSV(eventId, game, state, q, m, s, played, homeScore, awayScore, totalScore);


  const homeRaw = +(homePPS * GAME_SECONDS).toFixed(1);
  const homeAvg = +((avg(state.homeSamples)) * GAME_SECONDS).toFixed(1);
  const awayRaw = +(awayPPS * GAME_SECONDS).toFixed(1);
  const awayAvg = +((avg(state.awaySamples)) * GAME_SECONDS).toFixed(1);
  const totalRaw = +(totalPPS * GAME_SECONDS).toFixed(1);
  const totalAvg = +((avg(state.totalSamples)) * GAME_SECONDS).toFixed(1);

  const paceTrend = state.totalSamples.length >= 5 ? classifyPaceTrend(state.totalSamples) : "Not enough data";
  const homeMomentum = analyzeMomentum(state.homeSamples);
  const awayMomentum = analyzeMomentum(state.awaySamples);

  const scoreDiff = homeScore - awayScore;
  let leaderStatus = "TIED";
  if (Math.abs(scoreDiff) >= LEADER_THRESHOLD_POINTS) {
    leaderStatus = scoreDiff > 0 ? "HOME_LEADER" : "AWAY_LEADER";
  }
  state.lastLeaderStatus = leaderStatus;

  let homeTeamLine = null, awayTeamLine = null, homeLineDiff = '', awayLineDiff = '';
  if (oddsInfo && typeof oddsInfo.totalLine === 'number' && typeof oddsInfo.spread === 'number') {
    const teamTotals = calculateTeamTotals(oddsInfo.totalLine, oddsInfo.spread);
    
    if (oddsInfo.spread < 0) {
      homeTeamLine = teamTotals.high;
      awayTeamLine = teamTotals.low;
    } else {
      homeTeamLine = teamTotals.low;
      awayTeamLine = teamTotals.high;
    }
    
    homeLineDiff = +(homeAvg - homeTeamLine).toFixed(1);
    awayLineDiff = +(awayAvg - awayTeamLine).toFixed(1);
  }

  // ===== Q4 BETTING WINDOW =====
  if (q === 4 && !state.bettingWindowFired) {
    log('🎯 Q4 Betting window triggered');
    
    state.bettingWindowFired = true;
    state.bettingWindowProjection = totalAvg;
    state.bettingWindowLine = oddsInfo ? oddsInfo.totalLine : null;
    state.experimentalTotalLine = oddsInfo?.totalLine || null;
    state.experimentalHomeTeamLine = homeTeamLine;
    state.experimentalAwayTeamLine = awayTeamLine;

    if (oddsInfo && typeof oddsInfo.totalLine === 'number') {
      const diff = totalAvg - oddsInfo.totalLine;
      state.bettingWindowRecommendation = Math.abs(diff) >= ALERT_THRESHOLD_POINTS 
        ? (diff > 0 ? "OVER" : "UNDER") 
        : "NO BET";
    } else {
      state.bettingWindowRecommendation = "NO BET";
    }

    let homeTeamRec = "NO BET", awayTeamRec = "NO BET";
    if (homeTeamLine !== null && Math.abs(homeLineDiff) >= ALERT_THRESHOLD_POINTS) {
      homeTeamRec = homeLineDiff > 0 ? "OVER" : "UNDER";
    }
    if (awayTeamLine !== null && Math.abs(awayLineDiff) >= ALERT_THRESHOLD_POINTS) {
      awayTeamRec = awayLineDiff > 0 ? "OVER" : "UNDER";
    }

    state.homeTeamProjection = homeAvg;
    state.homeTeamLine = homeTeamLine;
    state.homeTeamRec = homeTeamRec;
    state.awayTeamProjection = awayAvg;
    state.awayTeamLine = awayTeamLine;
    state.awayTeamRec = awayTeamRec;

    const quarterLabel = q <= 4 ? `Q${q}` : `OT${q - 4}`;
    
    let bannerMessage = `⏰ **${getCurrentEDTTime()}**\n\n` +
      `🎯🚨 **BETTING DECISION WINDOW** 🚨🎯\n\n` +
      `**${game.home.name} vs. ${game.away.name}** [Game ${slot.charAt(4).toUpperCase()}]\n` +
      `⏱️ ${quarterLabel}, ${m}:${s.toString().padStart(2,'0')} | 📊 ${totalScore} (${homeScore}-${awayScore})\n\n` +
      `🏁 **FINAL CALL: Place wager now!**\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
      `💰 **GAME TOTAL (${totalScore})**\n\n` +
      `Avg: **${totalAvg}** | Line: **${oddsInfo ? oddsInfo.totalLine : 'N/A'}**\n` +
      `Diff: ${oddsInfo ? (totalAvg - oddsInfo.totalLine > 0 ? '+' : '') + (totalAvg - oddsInfo.totalLine).toFixed(1) : 'N/A'} pts | 🎯 **REC: ${state.bettingWindowRecommendation}${state.bettingWindowRecommendation !== "NO BET" ? ` ${oddsInfo ? oddsInfo.totalLine : 'N/A'}` : ''}**${state.bettingWindowRecommendation !== "NO BET" ? " ✅" : ""}\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
      `💰 **TEAM TOTALS**\n\n`;

    if (homeTeamLine !== null && awayTeamLine !== null) {
      bannerMessage += `**${game.home.name}** (${homeScore}) | Line: **${homeTeamLine}** | Avg: **${homeAvg}**\n` +
                   `Diff: ${homeLineDiff > 0 ? '+' : ''}${homeLineDiff} | 🎯 **REC: ${homeTeamRec}${homeTeamRec !== "NO BET" ? ` ${homeTeamLine}` : ""}**${homeTeamRec !== "NO BET" ? " ✅" : ""}\n\n` +
                   `**${game.away.name}** (${awayScore}) | Line: **${awayTeamLine}** | Avg: **${awayAvg}**\n` +
                   `Diff: ${awayLineDiff > 0 ? '+' : ''}${awayLineDiff} | 🎯 **REC: ${awayTeamRec}${awayTeamRec !== "NO BET" ? ` ${awayTeamLine}` : ""}**${awayTeamRec !== "NO BET" ? " ✅" : ""}\n\n`;
    }
    bannerMessage += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;

    // Experimental blended
    const blendRatio = 0.3;
    state.experimentalBlendedTotal = +((totalRaw * blendRatio) + (totalAvg * (1 - blendRatio))).toFixed(1);
    state.experimentalBlendedHome = +((homeRaw * blendRatio) + (homeAvg * (1 - blendRatio))).toFixed(1);
    state.experimentalBlendedAway = +((awayRaw * blendRatio) + (awayAvg * (1 - blendRatio))).toFixed(1);

    const expTotalDiff = state.experimentalBlendedTotal - (state.experimentalTotalLine || 0);
    const expHomeDiff = state.experimentalBlendedHome - (state.experimentalHomeTeamLine || 0);
    const expAwayDiff = state.experimentalBlendedAway - (state.experimentalAwayTeamLine || 0);

    const EXP_THRESHOLD = 1.5;

    state.experimentalTotalRec = Math.abs(expTotalDiff) >= EXP_THRESHOLD
      ? (expTotalDiff > 0 ? "OVER" : "UNDER")
      : "NO BET";

    state.experimentalHomeRec = homeTeamLine !== null && Math.abs(expHomeDiff) >= EXP_THRESHOLD
      ? (expHomeDiff > 0 ? "OVER" : "UNDER")
      : "NO BET";

    state.experimentalAwayRec = awayTeamLine !== null && Math.abs(expAwayDiff) >= EXP_THRESHOLD
      ? (expAwayDiff > 0 ? "OVER" : "UNDER")
      : "NO BET";

    let expAlert = 
      `⏰ **${getCurrentEDTTime()}**\n\n` +
      `🧪 **EXPERIMENTAL BLENDED PROJECTION** (⚠️ Beta)\n\n` +
      `**TOTAL:** Raw ${totalRaw} | Avg ${totalAvg} | Blend ${state.experimentalBlendedTotal} | Line ${oddsInfo?.totalLine || 'N/A'} | Diff ${(expTotalDiff > 0 ? '+' : '')}${expTotalDiff.toFixed(1)} | 🎯 **BET ${state.experimentalTotalRec}${state.experimentalTotalRec !== "NO BET" ? ` ${oddsInfo?.totalLine || 'N/A'}` : ''}**\n\n` +
      `**${game.home.name}:** Raw ${homeRaw} | Avg ${homeAvg} | Blend ${state.experimentalBlendedHome} | Line ${homeTeamLine || 'N/A'} | 🎯 **BET ${state.experimentalHomeRec}${state.experimentalHomeRec !== "NO BET" ? ` ${homeTeamLine}` : ''}**\n\n` +
      `**${game.away.name}:** Raw ${awayRaw} | Avg ${awayAvg} | Blend ${state.experimentalBlendedAway} | Line ${awayTeamLine || 'N/A'} | 🎯 **BET ${state.experimentalAwayRec}${state.experimentalAwayRec !== "NO BET" ? ` ${awayTeamLine}` : ''}**\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━\n`;

    state.decisionWindowComplete = true;
    state.lastAlert = Date.now();
    state.lastTimestamp = stamp;

    await sendAlert(bannerMessage, slot);
    log('✓ Main banner sent');
    
    await sendAlert(expAlert, slot);
    log('✓ Experimental alert sent');

    return;
  }

  // Post-decision game end checks
  if (state.decisionWindowComplete) {
    if (state.finalReportSent) {
      log('🔒 Final report already sent');
      return;
    }

    if (state.bettingWindowRecommendation === "OVER" && state.bettingWindowLine && totalScore > state.bettingWindowLine) {
      log('OVER locked in early');
      state.finalReportSent = true;
      await sendAlert(
        `⏰ **${getCurrentEDTTime()}**\n\n` +
        `✅ **OVER LOCKED** [Game ${slot.charAt(4).toUpperCase()}]\n\n` +
        `**${game.home.name} vs. ${game.away.name}**\n` +
        `Current: ${totalScore} > Line: ${state.bettingWindowLine}\n\n` +
        `Winner! 🎉\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━`,
        slot
      );
      delete trackedGames[slot];
      return;
    }

    if (q === 4 && m === 0 && s === 0 && homeScore !== awayScore && !state.finalReportSent) {
      log('Regulation ended');
      state.finalReportSent = true;
      await sendAlert(
        `⏰ **${getCurrentEDTTime()}**\n\n` +
        `🏁 **FINAL** [Game ${slot.charAt(4).toUpperCase()}]\n\n` +
        `**${game.home.name} vs. ${game.away.name}**\n` +
        `FINAL: ${homeScore}-${awayScore} (Total: ${totalScore})\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━`,
        slot
      );
      delete trackedGames[slot];
      return;
    }
  }

  // Pre-decision Q3+ alerts
  if (q < 3) {
    log(`Q${q}: Sampling only`);
    state.lastTimestamp = stamp;
    return;
  }

  if (state.silentMode && q < 3) {
    state.lastTimestamp = stamp;
    return;
  }

  if (q >= 3 && state.silentMode) {
    state.silentMode = false;
    log(`🎯 Q3 REACHED - Alerts now active`);
  }

  const now = Date.now();
  const quarterLabel = q <= 4 ? `Q${q}` : `OT${q - 4}`;

  if (!state.lastAlert || now - state.lastAlert >= ALERT_MIN_INTERVAL_MS) {
    let message = `⏰ **${getCurrentEDTTime()}**\n\n`;
    message += `**${game.home.name} vs. ${game.away.name}** [Game ${slot.charAt(4).toUpperCase()}]\n` +
               `⏱️ ${quarterLabel}, ${m}:${s.toString().padStart(2,'0')} | 📊 ${totalScore} (${homeScore}-${awayScore})\n\n` +
               `━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
               `📊 **PROJECTIONS**\n\n`;

    const homeLeaderLabel = leaderStatus === "HOME_LEADER" ? "| 👑 LEADER" : leaderStatus === "AWAY_LEADER" ? "| 🎯 UNDERDOG" : "";
    const awayLeaderLabel = leaderStatus === "AWAY_LEADER" ? "| 👑 LEADER" : leaderStatus === "HOME_LEADER" ? "| 🎯 UNDERDOG" : "";

    message += `**${game.home.name}** (${homeScore}) ${formatMomentumForDiscord(homeMomentum)} ${homeLeaderLabel}\n` +
               `Raw: ${homeRaw} | Avg: **${homeAvg}**\n` +
               `Line: **${homeTeamLine || 'N/A'}** | Diff: ${homeLineDiff > 0 ? '+' : ''}${homeLineDiff}\n\n`;

    message += `**${game.away.name}** (${awayScore}) ${formatMomentumForDiscord(awayMomentum)} ${awayLeaderLabel}\n` +
               `Raw: ${awayRaw} | Avg: **${awayAvg}**\n` +
               `Line: **${awayTeamLine || 'N/A'}** | Diff: ${awayLineDiff > 0 ? '+' : ''}${awayLineDiff}\n\n` +
               `━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
               `💰 **GAME TOTAL (${totalScore})**\n\n` +
               `Raw: ${totalRaw} | Avg: **${totalAvg}**\n` +
               `Line: **${oddsInfo ? oddsInfo.totalLine : 'N/A'}** | Diff: ${oddsInfo ? (totalAvg - oddsInfo.totalLine > 0 ? '+' : '') + (totalAvg - oddsInfo.totalLine).toFixed(1) : 'N/A'} pts\n\n` +
               `Samples: ${state.totalSamples.length}`;

    if (state.totalSamples.length >= 5) {
      message += ` | **Reliability: ${formatPaceTrendForDiscord(paceTrend)}**`;
    }

    message += `\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n`;

    log('Sending Q3+ projection alert');
    await sendAlert(message, slot);
    state.lastAlert = now;
  }

  state.lastTimestamp = stamp;
}

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => log(`🚀 Service listening on port ${PORT}`));
