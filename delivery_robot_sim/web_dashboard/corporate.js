/**
 * NexusDelivery — Corporate Experience Engine
 * Theme Manager (Light/Dark), Multi-Language Localization, 
 * Customer & Supervisor Auth Redirection, and Contact Dispatcher.
 */

// State
let currentTheme = localStorage.getItem('nexus_theme') || 'light';
let currentLang = localStorage.getItem('nexus_lang') || 'en';

/* ==========================================================================
   1. THEME SWITCHER (Light Default + Dark Mode)
   ========================================================================== */
function initTheme() {
  applyTheme(currentTheme);
}

function toggleTheme() {
  currentTheme = (currentTheme === 'light') ? 'dark' : 'light';
  localStorage.setItem('nexus_theme', currentTheme);
  applyTheme(currentTheme);
}

function applyTheme(theme) {
  const body = document.body;
  const icon = document.getElementById('themeToggleIcon');
  if (theme === 'dark') {
    body.classList.add('dark-theme');
    if (icon) icon.textContent = '☀️';
  } else {
    body.classList.remove('dark-theme');
    if (icon) icon.textContent = '🌙';
  }
}

/* ==========================================================================
   2. LANGUAGE LOCALIZATION (EN / FR / AR)
   ========================================================================== */
const I18N_STRINGS = {
  en: {
    heroTag: 'RESEARCH & ENGINEERING PROTOTYPE • TRL 3–4 SIMULATION BASELINE',
    heroTitle: 'Autonomous Sidewalk Robotics for Last-Mile Logistics',
    heroDesc: 'Next-generation zero-emission mobile robots engineered with vision-centric perception, topological corridor pathing, and deterministic multi-zone safety to deliver food, groceries, and medical supplies to curbside doorsteps.',
    btnLaunchCustomer: 'Launch Customer Portal 🚀',
    btnFleetOps: 'Fleet Operations 🛡️',
    statCost: '50% Lower',
    statCostSub: 'Urban Delivery Capex',
    statSpeed: '15 Min',
    statSpeedSub: 'Average Curbside Transit',
    statZero: 'Zero',
    statZeroSub: 'Direct Tailpipe Emissions',
    solTitle: 'Engineered for Modern Cities',
    solSub: 'Solving the urban delivery bottleneck through autonomous robotics and edge AI.'
  },
  fr: {
    heroTag: 'PROTOTYPE DE RECHERCHE ET INGÉNIERIE • TRL 3–4 SIMULATION',
    heroTitle: 'Robotique Autonome de Trottoir pour la Logistique du Dernier Kilomètre',
    heroDesc: 'Robots mobiles zéro-émission de nouvelle génération conçus avec une vision stéréo active, une navigation de couloir topologique et une sécurité prédictive pour livrer repas et colis aux pas de porte.',
    btnLaunchCustomer: 'Portail Client 🚀',
    btnFleetOps: 'Opérations Flotte 🛡️',
    statCost: '-50% Coût',
    statCostSub: 'Livraison Urbaine Capex',
    statSpeed: '15 Min',
    statSpeedSub: 'Transit Moyen Trottoir',
    statZero: 'Zéro',
    statZeroSub: 'Émissions Directes CO2',
    solTitle: 'Conçu pour les Villes Modernes',
    solSub: 'Résoudre le goulot d’étranglement urbain grâce à la robotique autonome et l’IA embarquée.'
  },
  ar: {
    heroTag: 'نموذج بحثي وهندسي تجريبي • مستوى الجاهزية TRL 3-4 للمحاكاة',
    heroTitle: 'روبوتات التوصيل الذاتي للأرصفة الحضرية والخدمات اللوجستية',
    heroDesc: 'جيل جديد من الروبوتات الكهربائية ذاتية القيادة المصممة برؤية مجسمة ذكية، مسارات أرصفة محددة، ونظام أمان متطور لتوصيل الطرود والطلبات حتى عتبة الباب مباشرة.',
    btnLaunchCustomer: 'بوابة العملاء 🚀',
    btnFleetOps: 'عمليات الأسطول 🛡️',
    statCost: 'وفر 50%',
    statCostSub: 'تكاليف التوصيل الحضري',
    statSpeed: '15 دقيقة',
    statSpeedSub: 'متوسط زمن التوصيل',
    statZero: 'صفر',
    statZeroSub: 'انبعاثات كربونية مباشرة',
    solTitle: 'مصمم للمدن الذكية الحديثة',
    solSub: 'حل أزمة التوصيل للميل الأخير عبر الروبوتات الذكية والذكاء الاصطناعي.'
  }
};

function changeLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('nexus_lang', lang);
  applyLanguage(lang);
}

function applyLanguage(lang) {
  const dict = I18N_STRINGS[lang] || I18N_STRINGS.en;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });

  const langSelect = document.getElementById('langSelect');
  if (langSelect) langSelect.value = lang;

  if (lang === 'ar') {
    document.documentElement.dir = 'rtl';
  } else {
    document.documentElement.dir = 'ltr';
  }
}

/* ==========================================================================
   3. AUTHENTICATION MODAL & NAVIGATION
   ========================================================================== */
function openAuthModal(tab = 'login', targetPortal = 'customer') {
  const backdrop = document.getElementById('authModalBackdrop');
  if (backdrop) backdrop.classList.add('active');
  switchAuthTab(tab);
  
  // Set intended destination
  window.intendedPortal = targetPortal;
}

function closeAuthModal() {
  const backdrop = document.getElementById('authModalBackdrop');
  if (backdrop) backdrop.classList.remove('active');
}

function switchAuthTab(tab) {
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();
  const errorEl = document.getElementById('loginErrorMsg');
  const submitBtn = document.getElementById('btnSubmitLogin');

  if (errorEl) errorEl.textContent = '';
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Verifying Credentials...'; }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.success && data.token) {
      localStorage.setItem('nexus_client_token', data.token);
      localStorage.setItem('nexus_user_role', data.user.role || 'CUSTOMER');
      
      const role = data.user.role || 'CUSTOMER';
      if (role === 'OPERATOR' || role === 'SUPER_ADMIN' || role === 'FLEET_MANAGER') {
        window.location.href = '/supervisor';
      } else {
        window.location.href = '/client';
      }
    } else {
      if (errorEl) errorEl.textContent = data.error || 'Invalid email address or password.';
    }
  } catch (err) {
    if (errorEl) errorEl.textContent = 'Network error. Please try again.';
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Sign In to Workspace'; }
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const phone = document.getElementById('regPhone').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();
  const address = document.getElementById('regAddress').value.trim();
  const errorEl = document.getElementById('registerErrorMsg');
  const submitBtn = document.getElementById('btnSubmitRegister');

  if (errorEl) errorEl.textContent = '';
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Creating Account...'; }

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, email, password, address })
    });
    const data = await res.json();
    if (data.success && data.token) {
      localStorage.setItem('nexus_client_token', data.token);
      localStorage.setItem('nexus_user_role', 'CUSTOMER');
      window.location.href = '/client';
    } else {
      if (errorEl) errorEl.textContent = data.error || 'Registration failed.';
    }
  } catch (err) {
    if (errorEl) errorEl.textContent = 'Network error. Please try again.';
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Create Customer Account'; }
  }
}

function fillDemoAccount(type) {
  if (type === 'customer') {
    document.getElementById('loginEmail').value = 'client@nexus.tn';
    document.getElementById('loginPassword').value = 'client123';
  } else if (type === 'supervisor') {
    document.getElementById('loginEmail').value = 'supervisor@nexus.tn';
    document.getElementById('loginPassword').value = 'nexus2026';
  }
}

/* ==========================================================================
   4. CONTACT INQUIRY HANDLER
   ========================================================================== */
function handleContactSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('contactName').value.trim();
  const email = document.getElementById('contactEmail').value.trim();
  const org = document.getElementById('contactOrg').value.trim();
  const msg = document.getElementById('contactMsg').value.trim();
  const feedback = document.getElementById('contactFeedback');

  if (feedback) {
    feedback.textContent = `Thank you, ${name}! Your inquiry from ${org || 'your organization'} has been logged. Our robotics partnerships team will contact ${email} shortly.`;
    feedback.style.color = 'var(--accent-emerald)';
  }
  e.target.reset();
}

/* ==========================================================================
   5. INITIALIZATION
   ========================================================================== */
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  applyLanguage(currentLang);
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('auth') === 'login') {
    openAuthModal('login');
  } else if (urlParams.get('auth') === 'register') {
    openAuthModal('register');
  } else if (urlParams.get('auth') === 'supervisor') {
    openAuthModal('login', 'supervisor');
    fillDemoAccount('supervisor');
  }
});
