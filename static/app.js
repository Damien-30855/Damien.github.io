// app.js — ลูกเล่นของหน้าเว็บ (ตกแต่งเท่านั้น ไม่แตะกติกาของระบบ)
//   1) แสงเรืองตามเมาส์        2) ปุ่มดูดเข้าหาเมาส์ / การ์ดมีแสงตามเมาส์
//   3) ตัวเลขบนการ์ดวิ่งขึ้น     4) เนื้อหาโผล่ขึ้นตอนเลื่อนถึง
// ถ้าผู้ใช้ตั้งค่า "ลดการเคลื่อนไหว" ในระบบปฏิบัติการ (หรือเบราว์เซอร์เก่ามาก) จะข้ามทั้งหมด
// หน้าเว็บยังใช้งานได้ครบทุกอย่าง เพราะทุกอย่างเป็น "เพิ่มความสวยงาม" ทับของเดิม
(function () {
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // ตรวจชนิดของ pointer ตอนขยับจริง (แม่นกว่าการเดาจาก media query):
  // เมาส์/ปากกา = ทำเอฟเฟกต์ · ลากนิ้วบนจอสัมผัส = ข้าม เพื่อไม่ให้ปุ่มสั่นตอนเลื่อนจอ
  var isTouchPointer = function (event) { return event.pointerType === 'touch'; };

  // ---------- 4) เนื้อหาโผล่ขึ้นตอนเลื่อนถึง ----------
  var revealTargets = document.querySelectorAll('.top, .cards > .card, .main > .panel, .main > .notice');
  if (!reduceMotion && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05, rootMargin: '0px 0px -6% 0px' });
    revealTargets.forEach(function (el) {
      el.classList.add('reveal');
      io.observe(el);
    });
  }

  // ---------- 3) ตัวเลขบนการ์ดวิ่งขึ้น ----------
  document.querySelectorAll('.card .num').forEach(function (el) {
    var target = parseInt(el.textContent.trim(), 10);
    if (reduceMotion || !isFinite(target)) return;      // ค่าที่ไม่ใช่ตัวเลข (เช่น "-") ปล่อยไว้
    var startTime = performance.now();
    var duration = 900;
    el.textContent = '0';
    var step = function (now) {
      var p = Math.min((now - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3);               // เร็วตอนแรก แล้วค่อย ๆ ช้า
      el.textContent = String(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });

  if (reduceMotion) return;                             // ผู้ใช้ปิดแอนิเมชัน: ไม่ต้องทำต่อ

  // ---------- 1) แสงเรืองตามเมาส์ ----------
  var pending = false;
  document.addEventListener('pointermove', function (e) {
    if (isTouchPointer(e) || pending) return;
    pending = true;
    var x = (e.clientX / window.innerWidth * 100).toFixed(2) + '%';
    var y = (e.clientY / window.innerHeight * 100).toFixed(2) + '%';
    requestAnimationFrame(function () {
      pending = false;
      document.documentElement.style.setProperty('--mx', x);
      document.documentElement.style.setProperty('--my', y);
    });
  }, { passive: true });

  // ---------- 2) การ์ด/แผง: แสงในตัวตามตำแหน่งเมาส์ ----------
  document.querySelectorAll('.card, .panel').forEach(function (el) {
    el.addEventListener('pointermove', function (e) {
      if (isTouchPointer(e)) return;
      var box = el.getBoundingClientRect();
      el.style.setProperty('--px', ((e.clientX - box.left) / box.width * 100).toFixed(1) + '%');
      el.style.setProperty('--py', ((e.clientY - box.top) / box.height * 100).toFixed(1) + '%');
    });
  });

  // ---------- 2) ปุ่ม/ลิงก์เมนู: ดูดเข้าหาเมาส์เล็กน้อย ----------
  var pull = 5;                                          // ระยะดูดสูงสุด (px)
  document.querySelectorAll('.btn, .nav a, .mbtn, .qty button').forEach(function (el) {
    if (el.disabled) return;
    el.addEventListener('pointermove', function (e) {
      if (isTouchPointer(e)) return;
      var box = el.getBoundingClientRect();
      var dx = (e.clientX - (box.left + box.width / 2)) / (box.width / 2);
      var dy = (e.clientY - (box.top + box.height / 2)) / (box.height / 2);
      el.style.transform = 'translate(' + (dx * pull).toFixed(2) + 'px,' + (dy * pull).toFixed(2) + 'px)';
    });
    var reset = function () { el.style.transform = ''; };
    ['pointerleave', 'pointerup', 'pointercancel', 'blur'].forEach(function (name) {
      el.addEventListener(name, reset);
    });
  });
})();
