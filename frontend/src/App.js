import React, { useRef, useState, useEffect, useCallback, useMemo } from "react";
import { Hands } from "@mediapipe/hands";
import { Camera } from "@mediapipe/camera_utils";
import "./App.css";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const PHRASES = ["Thank you", "Welcome", "Yes", "No", "Help", "Sorry", "Eat", "Hello", "Bye", "Stop"];
const MAX_Q = 30;
const DOUBLE_LETTER_COOLDOWN = 3000; 

const FALLBACK_WORDS = [
  "APPLE", "WATER", "SMILE", "HAPPY", "GREEN", "PLANT", "TIGER", "RIVER", "CLOUD", "BRAIN", 
  "LIGHT", "MUSIC", "WORLD", "HELLO", "REACT", "PYTHON", "CODING", "HOUSE", "MOUSE", "CHAIR", 
  "TABLE", "PHONE", "CLOCK", "WATCH", "TRAIN", "PLANE", "SPACE", "EARTH", "NIGHT", "OCEAN", 
  "BEACH", "HEART", "PEACE", "DREAM", "LAUGH", "YOUTH", "FAITH", "TRUST", "TRUTH", "BRAVE", 
  "SMART", "QUICK", "FLASH", "GHOST", "MAGIC", "DRAGON", "FAIRY", "QUEEN", "TRACK", "FIELD", 
  "SPORT", "SCORE", "MATCH", "BREAD", "FRUIT", "SWEET", "CANDY", "JUICE", "DRINK", "GLASS", 
  "PLATE", "SPOON", "KNIFE", "CHIEF", "GUARD", "PILOT", "NURSE", "BAKER", "DANCE", "SINGER", 
  "ACTOR", "MOVIE", "STAGE", "PAINT", "BRUSH", "COLOR", "BLACK", "WHITE", "BROWN", "YELLOW", 
  "ORANGE", "PURPLE", "SILVER", "METAL", "STONE", "BRICK", "PAPER", "PENCIL", "ERASER", "RULER", 
  "SCHOOL", "CLASS", "GRADE", "STUDY", "LEARN", "TEACH", "THINK", "SOLVE", "BUILD", "CREATE"
];

let wordPool = [];

const fetchRandomWord = async () => {
  if (wordPool.length > 0) return wordPool.pop();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000); 
  try {
    const res = await fetch(`https://random-word-api.herokuapp.com/word?number=20`, { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error("API Network error");
    const data = await res.json();
    wordPool = data.map(w => w.toUpperCase());
    return wordPool.pop();
  } catch (err) {
    clearTimeout(timeoutId);
    console.warn("API was too slow or failed. Using 100-word instant fallback.");
    return FALLBACK_WORDS[Math.floor(Math.random() * FALLBACK_WORDS.length)];
  }
};

function App() {
  const videoRef = useRef(null);
  const ws = useRef(null); 
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [tab, setTabState] = useState("home");
  const tabRef = useRef("home");

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('signLanguageTutorUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  const [quizStats, setQuizStats] = useState(() => {
    const savedStats = localStorage.getItem('signLanguageStats');
    return savedStats ? JSON.parse(savedStats) : [];
  });

  useEffect(() => {
    localStorage.setItem('signLanguageStats', JSON.stringify(quizStats));
  }, [quizStats]);

  const dashboardData = useMemo(() => {
    if (!quizStats || quizStats.length === 0) return null;
    let totalCorrect = 0;
    const letterData = {};
    LETTERS.forEach(l => letterData[l] = { attempts: 0, correct: 0, times: [] });

    quizStats.forEach(stat => {
      if (stat.correct) totalCorrect++;
      if (letterData[stat.letter]) {
        letterData[stat.letter].attempts++;
        if (stat.correct) letterData[stat.letter].correct++;
        if (stat.time !== "Wrong" && !isNaN(parseFloat(stat.time))) {
          letterData[stat.letter].times.push(parseFloat(stat.time));
        }
      }
    });

    const accuracy = Math.round((totalCorrect / quizStats.length) * 100);
    const heatmap = [];
    let validTimes = [];

    LETTERS.forEach(l => {
      const data = letterData[l];
      const acc = data.attempts > 0 ? data.correct / data.attempts : null;
      const avgTime = data.times.length > 0 ? (data.times.reduce((a,b)=>a+b,0) / data.times.length) : null;
      
      let status = "unpracticed";
      if (acc !== null) {
        if (acc >= 0.8) status = "good";
        else if (acc >= 0.5) status = "okay";
        else status = "bad";
      }

      heatmap.push({ letter: l, status, acc, avgTime, attempts: data.attempts });
      if (avgTime !== null && acc !== null) validTimes.push({ letter: l, avgTime, acc });
    });

    validTimes.sort((a, b) => a.avgTime - b.avgTime);
    const fastest = validTimes.slice(0, 3);
    const slowest = [...validTimes].reverse().slice(0, 3);
    const weakSpots = heatmap.filter(h => h.attempts > 0 && h.acc < 0.7).sort((a, b) => a.acc - b.acc).slice(0, 3);

    return { totalAttempts: quizStats.length, accuracy, heatmap, fastest, slowest, weakSpots };
  }, [quizStats]);

  const stableCharRef = useRef("");
  const stableCountRef = useRef(0);
  const lastAddedRef = useRef("");
  const handDetectedRef = useRef(false);
  const lastAddedTimeRef = useRef(0); 

  const quizActiveRef = useRef(false);
  const quizTargetRef = useRef("");
  const quizStartTimeRef = useRef(0);

  const wordActiveRef = useRef(false);
  const targetWordRef = useRef("");
  const wordIndexRef = useRef(0);
  const wordStartTimeRef = useRef(0);
  const wordHandDetectedRef = useRef(false);

  const phraseActiveRef = useRef(false);
  const phraseTargetRef = useRef("");
  const phraseStartTimeRef = useRef(0);
  const phraseHandDetectedRef = useRef(false);

  const [prediction, setPrediction] = useState("");
  const [isCameraRunning, setIsCameraRunning] = useState(false);

  const [sentence, setSentence] = useState("");
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [target, setTarget] = useState("");

  const [word, setWord] = useState("");
  const [wordProgress, setWordProgress] = useState(0);
  const [wordResults, setWordResults] = useState([]); 
  const [wordComplete, setWordComplete] = useState(false);
  const [isFetchingWord, setIsFetchingWord] = useState(false);

  const [phrase, setPhrase] = useState("");
  const [phraseResult, setPhraseResult] = useState(null); 

  const setTab = (newTab) => {
    setTabState(newTab);
    tabRef.current = newTab;
    setPrediction("");
  };

  const speakSentence = () => {
    if (!sentence) return;
    const utterance = new SpeechSynthesisUtterance(sentence);
    utterance.rate = 0.9; 
    window.speechSynthesis.speak(utterance);
  };

  // ================= APP LOGIC ROUTER =================
  const handleAppLogic = (currentPred) => {
    const currentTab = tabRef.current;

    if (currentTab === "sentence") {
      if (currentPred === stableCharRef.current) {
        stableCountRef.current += 1;
      } else {
        stableCharRef.current = currentPred;
        stableCountRef.current = 1;
      }

      const isSameAsLast = currentPred === lastAddedRef.current;
      const cooldownPassed = Date.now() - lastAddedTimeRef.current >= DOUBLE_LETTER_COOLDOWN;

      if (stableCountRef.current >= 3 && (!isSameAsLast || cooldownPassed)) {
        if (PHRASES.includes(currentPred)) {
          setSentence((prev) => {
            const prefix = prev.length > 0 && !prev.endsWith(" ") ? " " : "";
            return prev + prefix + currentPred + " ";
          });
        } else {
          setSentence((prev) => prev + currentPred);
        }
        lastAddedRef.current = currentPred;
        lastAddedTimeRef.current = Date.now();
        stableCountRef.current = 0;
      }
    }

    if (currentTab === "quiz" && quizActiveRef.current) {
      if (!handDetectedRef.current) {
        handDetectedRef.current = true;
        quizStartTimeRef.current = Date.now();
      }
      if (currentPred === quizTargetRef.current) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= 2) progressQuiz(true);
      } else {
        stableCountRef.current = 0;
      }
    }

    if (currentTab === "word" && wordActiveRef.current && !wordComplete) {
      if (!wordHandDetectedRef.current) {
        wordHandDetectedRef.current = true;
        wordStartTimeRef.current = Date.now();
      }
      const currentTargetLetter = targetWordRef.current[wordIndexRef.current];
      if (currentPred === currentTargetLetter) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= 2) progressWord(true);
      } else {
        stableCountRef.current = 0;
      }
    }

    if (currentTab === "phrases" && phraseActiveRef.current) {
      if (!phraseHandDetectedRef.current) {
        phraseHandDetectedRef.current = true;
        phraseStartTimeRef.current = Date.now();
      }
      if (currentPred === phraseTargetRef.current) {
        phraseActiveRef.current = false;
        setPhraseResult('correct');
      }
    }
  };

  const handleAppLogicRef = useRef(handleAppLogic);
  useEffect(() => { handleAppLogicRef.current = handleAppLogic; });

  // ================= WEBSOCKET CONNECTION =================
  useEffect(() => {
    let isMounted = true;
    let reconnectTimeout;

    const connect = () => {
      ws.current = new WebSocket("ws://127.0.0.1:8000/ws/predict");

      ws.current.onopen = () => console.log("🟢 Connected to AI Backend");
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "prediction") {
          const currentPred = data.label.trim();
          setPrediction(currentPred);
          handleAppLogicRef.current(currentPred); 
        } else if (data.type === "status") {
          setPrediction(`(${data.message})`);
        }
      };

      ws.current.onclose = () => {
        if (isMounted) {
          console.log("🔴 WebSocket Closed. Reconnecting in 2 seconds...");
          reconnectTimeout = setTimeout(connect, 2000);
        }
      };
    };

    connect(); 

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (ws.current) ws.current.close();
    };
  }, []);

  // ================= MEDIAPIPE CAMERA LOOP =================
  useEffect(() => {
    if (!isCameraRunning || !videoRef.current) return;

    const hands = new Hands({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
    });

    hands.setOptions({
      maxNumHands: 2,
      minDetectionConfidence: 0.7,
      minTrackingConfidence: 0.7
    });

    hands.onResults((results) => {
      let leftHand = new Array(63).fill(0.0);
      let rightHand = new Array(63).fill(0.0);

      if (results.multiHandLandmarks) {
        results.multiHandLandmarks.forEach((landmarks, index) => {
          const label = results.multiHandedness[index].label; 
          const coords = [];
          landmarks.forEach(lm => { coords.push(lm.x, lm.y, lm.z); });
          
          if (label === 'Right') leftHand = coords;
          else rightHand = coords;
        });
      }

      const currentTab = tabRef.current;
      const mode = (currentTab === "phrases" || currentTab === "sentence") ? "dynamic" : "static";
      
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        if (mode === "dynamic") {
          ws.current.send(JSON.stringify({ mode: "dynamic", landmarks: [...leftHand, ...rightHand] }));
        } else {
          const isLeftActive = leftHand.some(v => v !== 0);
          const isRightActive = rightHand.some(v => v !== 0);

          if (isRightActive || isLeftActive) {
             const activeHand = isRightActive ? rightHand : leftHand;
             const isLeftHand = !isRightActive;
             ws.current.send(JSON.stringify({ 
                mode: "static", 
                landmarks: activeHand, 
                isLeft: isLeftHand 
             }));
          }
        }
      }
    });

    const camera = new Camera(videoRef.current, {
      onFrame: async () => {
        if (
          videoRef.current && 
          videoRef.current.readyState >= 2 && 
          videoRef.current.videoWidth > 0
        ) {
          try {
            await hands.send({ image: videoRef.current });
          } catch (e) {
            console.warn("MediaPipe Frame Drop:", e);
          }
        }
      },
      width: 640,
      height: 480
    });

    setTimeout(() => {
      camera.start();
    }, 100);

    return () => {
      camera.stop();
      hands.close();
    };
  }, [isCameraRunning]);

  const startPhraseMode = () => {
    const randomPhrase = PHRASES[Math.floor(Math.random() * PHRASES.length)];
    setPhrase(randomPhrase);
    phraseTargetRef.current = randomPhrase;
    setPhraseResult(null);
    phraseActiveRef.current = true;
    phraseStartTimeRef.current = 0;
    phraseHandDetectedRef.current = false;
  };
  
  const progressWord = useCallback((isCorrect) => {
    setWordResults((prev) => [...prev, isCorrect]);
    wordIndexRef.current += 1;
    setWordProgress(wordIndexRef.current);
    stableCountRef.current = 0;
    wordHandDetectedRef.current = false;
    wordStartTimeRef.current = 0;

    if (wordIndexRef.current >= targetWordRef.current.length) {
      wordActiveRef.current = false;
      setWordComplete(true);
    }
  }, []);

  const startWordMode = async () => {
    setIsFetchingWord(true);
    const dynamicWord = await fetchRandomWord();
    setWord(dynamicWord);
    targetWordRef.current = dynamicWord;
    setWordProgress(0);
    setWordResults([]);
    wordIndexRef.current = 0;
    setWordComplete(false);
    wordActiveRef.current = true;
    stableCountRef.current = 0;
    wordHandDetectedRef.current = false;
    wordStartTimeRef.current = 0;
    setIsFetchingWord(false);
  };

  const progressQuiz = useCallback((isCorrect) => {
    const timeTaken = handDetectedRef.current 
      ? ((Date.now() - quizStartTimeRef.current) / 1000).toFixed(1) 
      : 0;

    setQuizStats((prev) => [...prev, { letter: quizTargetRef.current, correct: isCorrect, time: isCorrect ? timeTaken : "Wrong" }]);
    if (isCorrect) setScore((s) => s + 1);

    setTotal((prevTotal) => {
      const newTotal = prevTotal + 1;
      if (newTotal >= MAX_Q) {
        quizActiveRef.current = false;
        return newTotal;
      }
      const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
      setTarget(randomLetter);
      quizTargetRef.current = randomLetter;
      stableCountRef.current = 0;
      handDetectedRef.current = false;
      quizStartTimeRef.current = 0; 
      return newTotal;
    });
  }, []);

  const startQuiz = () => {
    setScore(0);
    setTotal(0);
    quizActiveRef.current = true;
    const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
    setTarget(randomLetter);
    quizTargetRef.current = randomLetter;
    stableCountRef.current = 0;
    handDetectedRef.current = false;
    quizStartTimeRef.current = 0;
  };

  useEffect(() => {
    const timerInterval = setInterval(() => {
      const now = Date.now();
      if (tabRef.current === "quiz" && quizActiveRef.current) {
        if (handDetectedRef.current && quizStartTimeRef.current > 0) {
          if (now - quizStartTimeRef.current >= 5000) progressQuiz(false); 
        }
      }
      if (tabRef.current === "word" && wordActiveRef.current && !wordComplete) {
        if (wordHandDetectedRef.current && wordStartTimeRef.current > 0) {
          if (now - wordStartTimeRef.current >= 5000) progressWord(false); 
        }
      }
      if (tabRef.current === "phrases" && phraseActiveRef.current) {
        if (phraseHandDetectedRef.current && phraseStartTimeRef.current > 0) {
          if (now - phraseStartTimeRef.current >= 10000) { 
            phraseActiveRef.current = false;
            setPhraseResult('wrong');
          }
        }
      }
    }, 500);
    return () => clearInterval(timerInterval);
  }, [progressQuiz, progressWord, wordComplete]);

  useEffect(() => {
    const handleKey = (e) => {
      if (tabRef.current !== "sentence") return;
      if (e.key === " ") {
        setSentence((prev) => prev + " ");
        lastAddedRef.current = ""; 
        lastAddedTimeRef.current = 0;
      } else if (e.key === "Backspace") {
        setSentence((prev) => prev.slice(0, -1));
        lastAddedRef.current = ""; 
        lastAddedTimeRef.current = 0;
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleLogout = () => {
    setUser(null); 
    setTab("home");
    localStorage.removeItem('signLanguageTutorUser'); 
  };

  const hideCameraTabs = ["home", "login", "dashboard", "guide"];

  return (
    <div className="app-layout">
      <header className="topbar">
        <div className="topbar-left">
          <button className="icon-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <span className="brand-logo" onClick={() => setTab("home")}>SignTutor</span>
        </div>
        
        <div className="topbar-right">
          {user ? (
            <div className="user-profile-nav">
              <div className="avatar">{user.name.charAt(0).toUpperCase()}</div>
              <span className="user-name">{user.name}</span>
              <button className="btn-outline red" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="btn primary" onClick={() => setTab("login")}>Log In</button>
          )}
        </div>
      </header>

      <div className="main-container">
        <aside className={`sidebar ${isSidebarOpen ? "open" : "closed"}`}>
          <nav className="sidebar-nav">
            <div className="nav-group">
              <button className={`nav-item ${tab === "home" ? "active" : ""}`} onClick={() => setTab("home")}>Home</button>
              {user && (
                <button className={`nav-item highlight ${tab === "dashboard" ? "active" : ""}`} onClick={() => setTab("dashboard")}>Dashboard</button>
              )}
            </div>
            
            <div className="nav-section-title">Learn</div>
            <div className="nav-group indented">
              <button className={`nav-item ${tab === "guide" ? "active" : ""}`} onClick={() => setTab("guide")}>Dictionary Guide</button>
            </div>
            
            <div className="nav-section-title">Practice</div>
            <div className="nav-group indented">
              <button className={`nav-item ${tab === "predict" ? "active" : ""}`} onClick={() => setTab("predict")}>Practice</button>
              <button className={`nav-item ${tab === "quiz" ? "active" : ""}`} onClick={() => setTab("quiz")}>Alphabet Quiz</button>
              <button className={`nav-item ${tab === "word" ? "active" : ""}`} onClick={() => setTab("word")}>Spelling Bee</button>
              <button className={`nav-item ${tab === "phrases" ? "active" : ""}`} onClick={() => setTab("phrases")}>Phrase Drills</button>
              <button className={`nav-item ${tab === "sentence" ? "active" : ""}`} onClick={() => setTab("sentence")}>Sign & Speak</button>
            </div>
          </nav>
        </aside>

        <main className="content-area">
          <div className="content-wrapper">

            {tab === "home" && (
              <div className="view-container center-text">
                <h1 className="hero-title">Master Sign Language with AI</h1>
                <p className="hero-subtitle">
                  Practice the alphabet, test your spelling speed, and drill real-world phrases with instant, real-time feedback.
                </p>
                <div className="button-group">
                  <button className="btn primary lg" onClick={() => setTab(user ? "dashboard" : "login")}>
                    {user ? "Go to Dashboard" : "Get Started"}
                  </button>
                  <button className="btn outline lg" onClick={() => setTab("guide")}>View Dictionary</button>
                </div>
              </div>
            )}

            {tab === "login" && (
              <div className="view-container">
                <div className="panel login-panel">
                  <h2>Welcome Back</h2>
                  <p className="subtitle">Sign in to track your progress</p>
                  
                  <div className="form-group">
                    <label>Email Address</label>
                    <input type="email" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} placeholder="name@example.com"/>
                  </div>
                  <div className="form-group">
                    <label>Password (Demo: Any)</label>
                    <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} placeholder="••••••••"/>
                  </div>
                  <button className="btn primary full-width" onClick={() => {
                      if(loginEmail.includes("@")) {
                        const newUser = { email: loginEmail, name: loginEmail.split("@")[0] };
                        setUser(newUser);
                        setTab("dashboard");
                        localStorage.setItem('signLanguageTutorUser', JSON.stringify(newUser));
                      } else { alert("Please enter a valid email to test the login."); }
                    }}>Continue</button>
                </div>
              </div>
            )}

            {tab === "dashboard" && user && (
              <div className="view-container align-left">
                <div className="dashboard-header">
                  <div>
                    <h2 className="section-title">Hello, {user.name}</h2>
                    <p className="subtitle">Here is your learning overview.</p>
                  </div>
                  <div className="badge success">Active Learner</div>
                </div>

                {!dashboardData ? (
                   <div className="empty-state panel">
                     <p>You haven't generated any practice data yet!</p>
                     <button className="btn primary mt-20" onClick={() => setTab("quiz")}>Take an Alphabet Quiz</button>
                   </div>
                ) : (
                  <div className="bento-layout">
                    <div className="bento-row">
                      <div className="bento-card stat-card">
                        <span className="bento-label">Questions Answered</span>
                        <span className="bento-value">{dashboardData.totalAttempts}</span>
                      </div>
                      <div className="bento-card stat-card">
                        <span className="bento-label">Global Accuracy</span>
                        <div className="bento-progress-container">
                          <span className="bento-value success">{dashboardData.accuracy}%</span>
                          <div className="progress-bar-bg">
                             <div className="progress-bar-fill" style={{ width: `${dashboardData.accuracy}%` }}></div>
                          </div>
                        </div>
                      </div>
                      <div className="bento-card stat-card">
                        <span className="bento-label">Daily Goal</span>
                        <span className="bento-value focus">15 min</span>
                      </div>
                    </div>

                    <div className="bento-row split-2-1">
                      <div className="bento-card">
                        <h3 className="bento-title">Alphabet Heatmap</h3>
                        <p className="bento-desc">Visual breakdown of your proficiency across all 26 letters.</p>
                        <div className="heatmap-grid">
                          {dashboardData.heatmap.map((h, i) => (
                            <div key={i} className={`heat-cell ${h.status}`} title={`${h.letter}: ${h.attempts > 0 ? Math.round(h.acc*100) + '%' : 'Unpracticed'}`}>{h.letter}</div>
                          ))}
                        </div>
                      </div>
                      <div className="bento-card flex-col">
                        <h3 className="bento-title">Needs Review</h3>
                        <p className="bento-desc">Your lowest accuracy signs.</p>
                        {dashboardData.weakSpots.length > 0 ? (
                          <div className="weak-spots-list">
                            {dashboardData.weakSpots.map((ws, i) => (
                              <div key={i} className="weak-item">
                                <div className="weak-letter">{ws.letter}</div>
                                <div className="weak-acc danger">{Math.round(ws.acc * 100)}% acc</div>
                              </div>
                            ))}
                            <button className="btn primary full-width mt-20" onClick={() => setTab("quiz")}>Drill Weak Spots</button>
                          </div>
                        ) : (<div className="empty-state-mini">All good! Keep practicing.</div>)}
                      </div>
                    </div>

                    <div className="bento-row split-half">
                      <div className="bento-card">
                        <h3 className="bento-title">⚡ Fastest Signs</h3>
                        <div className="leaderboard">
                          {dashboardData.fastest.length > 0 ? dashboardData.fastest.map((f, i) => (
                            <div key={i} className="leader-row"><span className="leader-rank">#{i+1}</span><span className="leader-letter">{f.letter}</span><span className="leader-time">{f.avgTime.toFixed(1)}s avg</span></div>
                          )) : <p className="bento-desc mt-20">Not enough data.</p>}
                        </div>
                      </div>
                      <div className="bento-card">
                        <h3 className="bento-title">🐢 Slowest Signs</h3>
                        <div className="leaderboard">
                          {dashboardData.slowest.length > 0 ? dashboardData.slowest.map((s, i) => (
                            <div key={i} className="leader-row"><span className="leader-rank">#{i+1}</span><span className="leader-letter">{s.letter}</span><span className="leader-time">{s.avgTime.toFixed(1)}s avg</span></div>
                          )) : <p className="bento-desc mt-20">Not enough data.</p>}
                        </div>
                      </div>
                    </div>

                    <div className="bento-row">
                      <div className="bento-card full-width">
                        <h3 className="bento-title">Recent Activity Log</h3>
                        <div className="stats-table-container">
                          <table className="stats-table">
                            <thead><tr><th>#</th><th>Letter</th><th>Result</th><th>Time</th></tr></thead>
                            <tbody>
                              {[...quizStats].reverse().slice(0, 10).map((stat, i) => (
                                <tr key={i} className={stat.correct ? "row-correct" : "row-wrong"}>
                                  <td>{quizStats.length - i}</td><td>{stat.letter}</td><td>{stat.correct ? "✅" : "❌"}</td><td>{stat.time}{stat.correct ? "s" : ""}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {tab === "guide" && (
              <div className="view-container align-left">
                <h2 className="section-title">Common Phrases</h2>
                <div className="dictionary-grid">
                  {PHRASES.map((p) => (
                    <div key={p} className="dict-card">
                      <img src={`/data/guide_images/${p.replace(/ /g, "_")}.png`} alt={`Sign ${p}`} onError={(e) => { e.target.src = "/data/guide_images/placeholder.png"; }} />
                      <p>{p}</p>
                    </div>
                  ))}
                </div>
                <h2 className="section-title" style={{ marginTop: "40px" }}>The Alphabet</h2>
                <div className="dictionary-grid">
                  {LETTERS.map((l) => (
                    <div key={l} className="dict-card"><img src={`/data/guide_images/Sign_language_${l}.png`} alt={`Sign ${l}`} /><p>{l}</p></div>
                  ))}
                </div>
              </div>
            )}

            {!hideCameraTabs.includes(tab) && (
              <div className="practice-layout">
                <div className="camera-section">
                  <div className="camera-wrapper">
                    <video ref={videoRef} autoPlay playsInline muted />
                    {!isCameraRunning && (
                      <div className="camera-overlay">
                        <button className="btn primary" onClick={() => setIsCameraRunning(true)}>Enable Camera Feed</button>
                      </div>
                    )}
                  </div>
                  {isCameraRunning && (
                    <div className="live-status">
                      <span className="status-indicator"></span>
                      Live Translation: <strong>{prediction || "Waiting for sign..."}</strong>
                    </div>
                  )}
                </div>

                <div className="practice-content">
                  {tab === "predict" && (
                    <div className="view-container">
                      <h2 className="section-title">Practice Mode</h2>
                      <p className="subtitle">Show any sign to the camera to see the translation.</p>
                    </div>
                  )}

                  {tab === "quiz" && (
                    <div className="view-container">
                      {!quizActiveRef.current && total < MAX_Q && total === 0 ? (
                        <button className="btn primary lg" onClick={startQuiz}>Start Alphabet Quiz</button>
                      ) : total >= MAX_Q ? (
                        <div className="panel result-panel">
                          <h2>Quiz Complete</h2>
                          <h1 className="huge-score">{score} / {MAX_Q}</h1>
                          <button className="btn primary mt-20" onClick={startQuiz}>Play Again</button>
                        </div>
                      ) : (
                        <div className="panel active-panel">
                          <p className="subtitle">Question {total + 1} of {MAX_Q} — Score: {score}</p>
                          <h1 className="target-display">{target}</h1>
                          <button className="btn outline red mt-20" onClick={() => progressQuiz(false)}>Skip / Mark Wrong</button>
                        </div>
                      )}
                    </div>
                  )}

                  {tab === "word" && (
                    <div className="view-container">
                      {!wordActiveRef.current && !wordComplete ? (
                         <button className="btn primary lg" onClick={startWordMode} disabled={isFetchingWord}>
                           {isFetchingWord ? "Loading..." : "Start Spelling Bee"}
                         </button>
                      ) : wordComplete ? (
                        <div className="panel result-panel">
                          <h2>Word Completed</h2>
                          <div className="word-blocks mt-20">
                            {word.split("").map((char, i) => (<span key={i} className={`block ${wordResults[i] ? "success" : "danger"}`}>{char}</span>))}
                          </div>
                          <button className="btn primary mt-20" onClick={startWordMode} disabled={isFetchingWord}>
                            {isFetchingWord ? "Loading..." : "Next Word"}
                          </button>
                        </div>
                      ) : (
                        <div className="panel active-panel">
                          <p className="subtitle">5 seconds per letter</p>
                          <div className="word-blocks mt-20">
                            {word.split("").map((char, i) => {
                              let status = "";
                              if (i === wordProgress) status = "current";
                              else if (i < wordProgress) status = wordResults[i] ? "success" : "danger";
                              return (<span key={i} className={`block ${status}`}>{char}</span>);
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {tab === "phrases" && (
                    <div className="view-container">
                      {!phrase ? (
                         <button className="btn primary lg" onClick={startPhraseMode}>Start Phrase Drills</button>
                      ) : phraseResult === 'correct' ? (
                        <div className="panel result-panel">
                          <h2>Excellent!</h2>
                          <h1 className="target-display success">{phrase}</h1>
                          <button className="btn primary mt-20" onClick={startPhraseMode}>Next Drill</button>
                        </div>
                      ) : phraseResult === 'wrong' ? (
                        <div className="panel result-panel">
                          <h2>Time's Up ⏳</h2>
                          <h1 className="target-display danger">{phrase}</h1>
                          <button className="btn primary mt-20" onClick={startPhraseMode}>Try Another</button>
                        </div>
                      ) : (
                        <div className="panel active-panel">
                          <p className="subtitle">Perform the drill within 10 seconds</p>
                          <h1 className="target-display">{phrase}</h1>
                        </div>
                      )}
                    </div>
                  )}

                  {tab === "sentence" && (
                    <div className="view-container">
                      <h2 className="section-title" style={{marginBottom: "24px"}}>Sign & Speak</h2>
                      <div className="panel typer-panel">
                        <h2 className="typed-sentence">{sentence || <span className="placeholder">Start signing to compose text...</span>}</h2>
                      </div>
                      <div className="button-group mt-20">
                        <button className="btn primary" onClick={speakSentence} disabled={!sentence}>Speak</button>
                        <button className="btn outline red" onClick={() => { setSentence(""); lastAddedRef.current = ""; lastAddedTimeRef.current = 0;}}>Clear</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;