#!/usr/bin/env python3
"""v3.0 Phase 1 upgrade script - injects all new features into index.html"""
import re, sys

with open('index.html', 'r') as f:
    content = f.read()

changes = []

# ============ 1. Tab rename ============
old = '<div class="tab active" onclick="switchTab(\'dashboard\')">📊 仪表盘</div>'
new = '<div class="tab active" onclick="switchTab(\'dashboard\')">📋 工作台</div>'
if old in content:
    content = content.replace(old, new)
    changes.append('1. Tab renamed: 仪表盘 -> 工作台')
else:
    print('ERROR: tab rename target not found'); sys.exit(1)

# ============ 2. Insert new functions after huid() ============
anchor = "function huid() { return 'h_'+Date.now()+'_'+Math.random().toString(36).slice(2,6); }"
if anchor not in content:
    print('ERROR: huid anchor not found'); sys.exit(1)

new_functions = r'''
// ============================================================
// v3.0: 客户交互时间线 + 跟进提醒 + 智能分层 + 会面简报
// ============================================================
function iid() { return 'i_'+Date.now()+'_'+Math.random().toString(36).slice(2,6); }

function getClientInteractions(clientId) {
  var c = loadClients().find(function(x){return x.id===clientId});
  return (c && c.interactions) ? c.interactions : [];
}

function addInteraction(clientId, type, content, nextStepDue, nextStepNote) {
  var clients = loadClients();
  var ci = clients.findIndex(function(x){return x.id===clientId});
  if (ci < 0) return;
  if (!clients[ci].interactions) clients[ci].interactions = [];
  var interaction = {
    id: iid(), type: type||'note', content: content||'',
    date: new Date().toISOString().slice(0,10), createdAt: Date.now(),
    nextStepDue: nextStepDue||null, nextStepNote: nextStepNote||''
  };
  clients[ci].interactions.unshift(interaction);
  saveClients(clients);
  return interaction;
}

function deleteInteraction(clientId, interactionId) {
  var clients = loadClients();
  var ci = clients.findIndex(function(x){return x.id===clientId});
  if (ci < 0) return;
  clients[ci].interactions = (clients[ci].interactions||[]).filter(function(i){return i.id!==interactionId});
  saveClients(clients);
}

function completeInteractionFollowup(clientId, interactionId) {
  var clients = loadClients();
  var ci = clients.findIndex(function(x){return x.id===clientId});
  if (ci < 0) return;
  var inter = (clients[ci].interactions||[]).find(function(i){return i.id===interactionId});
  if (inter) { inter.nextStepDue = null; inter.nextStepNote = ''; saveClients(clients); }
}

function getAllReminders() {
  var clients = loadClients();
  var today = new Date().toISOString().slice(0,10);
  var reminders = [];
  for (var i=0; i<clients.length; i++) {
    var c = clients[i];
    if (c.interactions) {
      for (var j=0; j<c.interactions.length; j++) {
        var inter = c.interactions[j];
        if (inter.nextStepDue) {
          reminders.push({
            clientId: c.id, clientName: c.name, type: 'followup',
            dueDate: inter.nextStepDue,
            note: inter.nextStepNote || (inter.content||'').slice(0,30),
            interactionId: inter.id, overdue: inter.nextStepDue < today
          });
        }
      }
    }
    if (c.birthday) {
      var bd = new Date(c.birthday);
      var todayDate = new Date();
      var thisYearBd = new Date(todayDate.getFullYear(), bd.getMonth(), bd.getDate());
      var daysToBd = Math.ceil((thisYearBd - todayDate)/86400000);
      if (daysToBd >= 0 && daysToBd <= 7) {
        reminders.push({
          clientId: c.id, clientName: c.name, type: 'birthday',
          dueDate: thisYearBd.toISOString().slice(0,10),
          note: c.name+'生日 ('+(bd.getMonth()+1)+'月'+bd.getDate()+'日)',
          overdue: false, daysToBd: daysToBd
        });
      }
    }
  }
  reminders.sort(function(a,b){return a.dueDate.localeCompare(b.dueDate)});
  return reminders;
}

function getClientTier(client) {
  var assets = client.totalAssets||0;
  var interactions = client.interactions||[];
  var now = new Date();
  var lastInterDate = null;
  if (interactions.length > 0) lastInterDate = interactions[0].date;
  else if (client.createdAt) lastInterDate = client.createdAt;
  var daysSinceInter = 999;
  if (lastInterDate) daysSinceInter = Math.floor((now - new Date(lastInterDate))/86400000);
  if (daysSinceInter >= 90) return {tier:'D',label:'流失风险',color:'#ef4444',bg:'#fef2f2',desc:daysSinceInter+'天未交互'};
  if (assets >= 100) return {tier:'A',label:'高净值',color:'#7c3aed',bg:'#f5f3ff',desc:assets+'万资产'};
  if (assets >= 30 && daysSinceInter <= 30) return {tier:'B',label:'活跃',color:'#059669',bg:'#ecfdf5',desc:assets+'万 · 活跃'};
  return {tier:'C',label:'普通',color:'#6b7280',bg:'#f9fafb',desc:assets+'万'};
}

function renderTimeline(clientId) {
  var interactions = getClientInteractions(clientId);
  var typeIcons = {meeting:'🤝',call:'📞',wechat:'💬',note:'📝'};
  var typeLabels = {meeting:'会面',call:'电话',wechat:'微信',note:'笔记'};
  var today = new Date().toISOString().slice(0,10);
  var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 10px;"><div style="font-weight:600;font-size:0.9rem;">📅 交互时间线 ('+interactions.length+')</div><button onclick="showAddInteraction(\''+clientId+'\')" style="font-size:0.75rem;padding:4px 12px;background:var(--red);color:#fff;border:none;border-radius:6px;cursor:pointer;">+ 记录交互</button></div>';
  if (interactions.length === 0) {
    html += '<div style="text-align:center;color:var(--gray);padding:20px;font-size:0.8rem;">暂无交互记录<br><span style="font-size:0.7rem;">点击"记录交互"添加会面/电话/微信沟通记录</span></div>';
  } else {
    for (var i=0; i<interactions.length; i++) {
      var inter = interactions[i];
      var icon = typeIcons[inter.type]||'📝';
      var label = typeLabels[inter.type]||'笔记';
      var overdue = inter.nextStepDue && inter.nextStepDue < today;
      html += '<div style="background:#fff;border-radius:8px;padding:10px;margin-bottom:8px;border:1px solid #e5e7eb;border-left:3px solid '+(overdue?'#ef4444':'#e5e7eb')+';">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;">';
      html += '<div style="flex:1;"><span style="font-size:0.9rem;">'+icon+'</span> <span style="font-size:0.65rem;color:var(--gray);background:#f3f4f6;padding:1px 6px;border-radius:4px;">'+label+'</span> <span style="font-size:0.7rem;color:var(--gray);">'+(inter.date||'')+'</span></div>';
      html += '<button onclick="deleteInteraction(\''+clientId+'\',\''+inter.id+'\');viewClient(\''+clientId+'\')" style="font-size:0.6rem;padding:2px 6px;border:1px solid #fecaca;border-radius:4px;background:#fef2f2;color:#c41230;cursor:pointer;">删除</button>';
      html += '</div>';
      html += '<div style="font-size:0.82rem;margin-top:4px;white-space:pre-wrap;">'+(inter.content||'')+'</div>';
      if (inter.nextStepDue) {
        html += '<div style="margin-top:6px;padding:6px 8px;background:'+(overdue?'#fef2f2':'#fffbeb')+';border-radius:6px;font-size:0.72rem;">';
        html += '<span style="'+(overdue?'color:#ef4444;':'color:#f59e0b;')+'">⏰ 下次跟进：'+inter.nextStepDue+'</span>';
        if (inter.nextStepNote) html += ' <span style="color:var(--gray);">'+inter.nextStepNote+'</span>';
        html += ' <button onclick="completeInteractionFollowup(\''+clientId+'\',\''+inter.id+'\');viewClient(\''+clientId+'\')" style="font-size:0.6rem;padding:1px 6px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;margin-left:4px;">✓ 已完成</button>';
        html += '</div>';
      }
      html += '</div>';
    }
  }
  return html;
}

function showAddInteraction(clientId) {
  var html = '<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;justify-content:center;align-items:flex-end;"><div style="background:#fff;border-radius:16px 16px 0 0;width:100%;max-width:500px;max-height:85vh;overflow-y:auto;padding:20px;">';
  html += '<div style="font-weight:700;font-size:1.1rem;margin-bottom:12px;">📅 记录客户交互</div>';
  html += '<div style="margin-bottom:12px;"><div style="font-size:0.75rem;color:var(--gray);margin-bottom:4px;">交互类型</div><div style="display:flex;gap:6px;">';
  var types = [['meeting','🤝 会面'],['call','📞 电话'],['wechat','💬 微信'],['note','📝 笔记']];
  for (var i=0; i<types.length; i++) {
    html += '<button onclick="document.getElementById(\'interType\').value=\''+types[i][0]+'\';updateInterTypeBtns()" class="inter-type-btn" data-v="'+types[i][0]+'" style="flex:1;padding:8px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:0.78rem;cursor:pointer;">'+types[i][1]+'</button>';
  }
  html += '<input type="hidden" id="interType" value="note"></div></div>';
  html += '<div style="margin-bottom:12px;"><div style="font-size:0.75rem;color:var(--gray);margin-bottom:4px;">沟通内容（一句话即可）</div><textarea id="interContent" rows="3" placeholder="如：客户对近期的债基回撤比较担心，解释了利率波动影响，建议继续持有..." style="width:100%;padding:10px;border:1px solid #e5e7eb;border-radius:8px;font-size:0.85rem;"></textarea></div>';
  html += '<div style="margin-bottom:12px;"><div style="font-size:0.75rem;color:var(--gray);margin-bottom:4px;">下次跟进日期（选填）</div><div style="display:flex;gap:8px;align-items:center;"><input id="interNextDate" type="date" style="flex:1;padding:8px;border:1px solid #e5e7eb;border-radius:6px;font-size:0.85rem;">';
  html += '<select onchange="if(this.value){var d=new Date();d.setDate(d.getDate()+parseInt(this.value));document.getElementById(\'interNextDate\').value=d.toISOString().slice(0,10);}" style="padding:8px;border:1px solid #e5e7eb;border-radius:6px;font-size:0.8rem;"><option value="">快捷</option><option value="3">3天后</option><option value="7">1周后</option><option value="14">2周后</option><option value="30">1月后</option></select></div></div>';
  html += '<div style="margin-bottom:12px;"><div style="font-size:0.75rem;color:var(--gray);margin-bottom:4px;">跟进事项（选填）</div><input id="interNextNote" placeholder="如：发送产品资料、邀约面谈..." style="width:100%;padding:8px;border:1px solid #e5e7eb;border-radius:6px;font-size:0.85rem;"></div>';
  html += '<div style="display:flex;gap:8px;"><button onclick="closeModal()" style="flex:1;padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;font-size:0.85rem;cursor:pointer;">取消</button><button onclick="saveInteraction(\''+clientId+'\')" style="flex:1;padding:10px;border:none;border-radius:8px;background:var(--red);color:#fff;font-size:0.85rem;cursor:pointer;">保存</button></div></div></div>';
  document.getElementById('modalHost').innerHTML = html;
  updateInterTypeBtns();
}

function updateInterTypeBtns() {
  var v = document.getElementById('interType').value;
  document.querySelectorAll('.inter-type-btn').forEach(function(b){
    b.style.background = b.dataset.v===v?'var(--red)':'#fff';
    b.style.color = b.dataset.v===v?'#fff':'var(--dark)';
    b.style.border = b.dataset.v===v?'none':'1px solid #e5e7eb';
  });
}

function saveInteraction(clientId) {
  var type = document.getElementById('interType').value;
  var content = document.getElementById('interContent').value.trim();
  var nextDue = document.getElementById('interNextDate').value;
  var nextNote = document.getElementById('interNextNote').value.trim();
  if (!content) { toast('请输入沟通内容'); return; }
  addInteraction(clientId, type, content, nextDue, nextNote);
  closeModal();
  viewClient(clientId);
  toast('✅ 交互已记录'+(nextDue?' · 跟进提醒：'+nextDue:''));
}

async function generateMeetingBriefing(clientId) {
  var c = loadClients().find(function(x){return x.id===clientId});
  if (!c) return;
  var aiKey = getAiKey();
  if (!aiKey) { toast('请先在AI助手设置 DeepSeek Key'); return; }
  var btn = document.getElementById('btnBriefing');
  if (btn) { btn.disabled = true; btn.textContent = '🤖 生成中...'; }
  var interactions = c.interactions||[];
  var hds = c.holdings||[];
  var riskNames = {PR1:'保守型',PR2:'稳健型',PR3:'平衡型',PR4:'成长型',PR5:'进取型'};
  var prompt = '你是理财经理的AI助手，请为即将进行的客户会面生成一份简报。要求：简洁实用，理财经理10秒内能看完，400字以内。\n\n';
  prompt += '【客户基本信息】\n姓名：'+(c.name||'')+'\n风险等级：'+(riskNames[c.riskLevel]||c.riskLevel||'')+'\n可投资产：'+(c.totalAssets||0)+'万\n投资期限：'+(c.termMonths||'')+'个月\n';
  if (c.tags) prompt += '标签：'+c.tags+'\n';
  prompt += '\n【当前持仓】\n';
  if (hds.length > 0) {
    for (var i=0; i<Math.min(hds.length,5); i++) {
      var h = hds[i];
      prompt += '- '+(h.fundName||h.fundCode)+'：成本'+(h.buyAmount||0)+'元，盈亏'+((h.pnl||0)>=0?'+':'')+(h.pnl||0).toFixed(0)+'元\n';
    }
  } else { prompt += '暂无持仓记录\n'; }
  prompt += '\n【近期交互记录】\n';
  if (interactions.length > 0) {
    var typeLabels = {meeting:'会面',call:'电话',wechat:'微信',note:'笔记'};
    for (var i=0; i<Math.min(interactions.length,3); i++) {
      var inter = interactions[i];
      prompt += (inter.date||'')+' ['+(typeLabels[inter.type]||'笔记')+'] '+(inter.content||'').slice(0,80)+'\n';
    }
  } else { prompt += '暂无历史交互记录\n'; }
  var market = (typeof MARKET!=='undefined')?MARKET:{};
  var ap = (market.asset_prices)||{};
  prompt += '\n【市场环境】上证'+((ap.a_share||{}).level||'—')+' | 黄金'+((ap.gold||{}).level||'—')+'\n';
  prompt += '\n请按以下格式输出：\n## 客户概况\n（一句话画像）\n## 上次沟通要点\n（提炼最近1-2次交互的关键信息）\n## 潜在需求\n（基于持仓和画像推测2-3个需求点）\n## 推荐话术\n（1-2句开场白）\n## 建议产品\n（从产品库推荐2-3款，说明理由）';
  try {
    var resp = await fetch('https://api.deepseek.com/chat/completions', {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+aiKey},
      body:JSON.stringify({model:'deepseek-chat',messages:[{role:'user',content:prompt}],temperature:0.7,max_tokens:800})
    });
    if (!resp.ok) throw new Error('HTTP '+resp.status);
    var data = await resp.json();
    var briefing = data.choices[0].message.content;
    var html = '<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;justify-content:center;align-items:flex-end;"><div style="background:#fff;border-radius:16px 16px 0 0;width:100%;max-width:500px;max-height:85vh;overflow-y:auto;padding:20px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><div style="font-weight:700;font-size:1.1rem;">📋 会面简报 — '+(c.name||'')+'</div><button onclick="closeModal()" style="background:none;border:none;font-size:1.2rem;cursor:pointer;">✕</button></div>';
    html += '<div id="briefingContent" style="font-size:0.82rem;line-height:1.8;">'+renderMarkdown(briefing)+'</div>';
    html += '<div style="display:flex;gap:8px;margin-top:12px;"><button onclick="copyBriefing()" style="flex:1;padding:10px;border:none;border-radius:8px;background:var(--red);color:#fff;font-size:0.85rem;cursor:pointer;">📋 复制到剪贴板</button><button onclick="closeModal()" style="flex:1;padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;font-size:0.85rem;cursor:pointer;">关闭</button></div></div></div>';
    document.getElementById('modalHost').innerHTML = html;
    window._lastBriefing = briefing;
    toast('✅ 简报已生成');
  } catch(e) {
    toast('简报生成失败: '+e.message);
  }
  if (btn) { btn.disabled = false; btn.textContent = '📋 会面准备'; }
}

function copyBriefing() {
  var text = window._lastBriefing||'';
  navigator.clipboard.writeText(text).then(function(){
    toast('✅ 已复制，可粘贴到微信或备忘录');
  }).catch(function(){
    var ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    toast('✅ 已复制到剪贴板');
  });
}
'''

content = content.replace(anchor, anchor + '\n' + new_functions)
changes.append('2. New functions inserted (interactions, reminders, tiering, timeline, briefing)')

# ============ 3. Replace renderDashboard with renderWorkspace ============
# Find the function boundaries
rd_start = content.index('function renderDashboard() {')
# Find the matching closing brace by counting braces
brace_count = 0
i = rd_start
found_start = False
while i < len(content):
    if content[i] == '{':
        brace_count += 1
        found_start = True
    elif content[i] == '}':
        brace_count -= 1
        if found_start and brace_count == 0:
            rd_end = i + 1
            break
    i += 1

old_dashboard = content[rd_start:rd_end]

new_workspace = r'''function renderWorkspace() {
  var container = document.getElementById('dashboardContent');
  if (!container) { console.error('dashboardContent not found'); return; }
  try {
    var clients = loadClients();
    var now = new Date();
    var today = now.toISOString().slice(0,10);
    var allReminders = getAllReminders();
    var overdueReminders = allReminders.filter(function(r){return r.overdue});
    var upcomingReminders = allReminders.filter(function(r){return !r.overdue}).slice(0,5);
    var recentInteractions = [];
    for (var i=0; i<clients.length; i++) {
      var c = clients[i];
      if (c.interactions) {
        for (var j=0; j<c.interactions.length; j++) {
          recentInteractions.push(Object.assign({}, c.interactions[j], {clientName:c.name, clientId:c.id}));
        }
      }
    }
    recentInteractions.sort(function(a,b){return (b.createdAt||0)-(a.createdAt||0)});
    recentInteractions = recentInteractions.slice(0,5);
    var ap = (typeof MARKET!=='undefined'&&MARKET.asset_prices)?MARKET.asset_prices:{};
    var ss=ap.a_share||{}, g=ap.gold||{}, fx=ap.fx||{}, bond=ap.bond||{};
    var alerts = [];
    var alertCfg = loadAlertConfig();
    var totalPnl = clients.reduce(function(s,c){return s+(c.holdings||[]).reduce(function(ss,h){return ss+(h.pnl||0)},0)},0);
    for (var i=0; i<clients.length; i++) {
      var c = clients[i];
      for (var j=0; j<(c.holdings||[]).length; j++) {
        var h = c.holdings[j];
        if (h.buyDate && alertCfg.holding_days > 0) {
          var buy = new Date(h.buyDate);
          var days = Math.floor((now-buy)/86400000);
          if (days >= alertCfg.holding_days) alerts.push({icon:'📆',text:c.name+' '+(h.fundName||h.fundCode)+' 已持'+days+'天'});
        }
        if (h.pnl < -Math.abs(alertCfg.loss_threshold)) alerts.push({icon:'⚠',text:c.name+' '+(h.fundName||h.fundCode)+' 亏损'+(h.pnl||0).toFixed(0)+'元'});
        if (h._downDays >= (alertCfg.down_days||3)) alerts.push({icon:'📉',text:c.name+' '+(h.fundName||h.fundCode)+' 连跌'+h._downDays+'天'});
      }
    }
    if (alerts.length > 10) alerts.length = 10;
    var html = '';
    var hour = now.getHours();
    var greeting = '早上好';
    if (hour >= 12 && hour < 18) greeting = '下午好';
    else if (hour >= 18) greeting = '晚上好';
    html += '<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;border-radius:12px;padding:14px;margin-bottom:12px;">';
    html += '<div style="font-size:1rem;font-weight:700;">'+greeting+'！今天是 '+now.toLocaleDateString('zh-CN',{weekday:'long',month:'long',day:'numeric'})+'</div>';
    html += '<div style="display:flex;gap:12px;font-size:0.75rem;margin-top:6px;opacity:0.8;flex-wrap:wrap;">';
    html += '<span>📈 上证 '+(ss.level||'—')+'</span><span>💰 黄金 '+(g.level||'—')+'</span><span>💱 汇率 '+(fx.level||'—')+'</span><span>📊 国债 '+(bond.cn_10y||'—')+'</span>';
    html += '</div></div>';
    html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">';
    html += '<div style="background:#f0fdf4;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:0.65rem;color:var(--gray);">管理客户</div><div style="font-size:1.2rem;font-weight:700;">'+clients.length+'</div></div>';
    html += '<div style="background:'+(overdueReminders.length>0?'#fef2f2':'#eff6ff')+';border-radius:10px;padding:10px;text-align:center;"><div style="font-size:0.65rem;color:var(--gray);">待跟进</div><div style="font-size:1.2rem;font-weight:700;color:'+(overdueReminders.length>0?'#ef4444':'#1e40af')+';">'+allReminders.length+'</div></div>';
    html += '<div style="background:#fef2f2;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:0.65rem;color:var(--gray);">持仓盈亏</div><div style="font-size:1.2rem;font-weight:700;color:'+(totalPnl>=0?'#c41230':'#059669')+';">'+(totalPnl>=0?'+':'')+totalPnl.toFixed(0)+'</div></div>';
    html += '</div>';
    if (overdueReminders.length > 0) {
      html += '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:10px;margin-bottom:10px;">';
      html += '<div style="font-weight:600;font-size:0.85rem;color:#ef4444;margin-bottom:6px;">🔴 逾期未跟进 ('+overdueReminders.length+')</div>';
      for (var i=0; i<Math.min(overdueReminders.length,5); i++) {
        var r = overdueReminders[i];
        var typeIcon = r.type==='birthday'?'🎂':'⏰';
        html += '<div onclick="viewClient(\''+r.clientId+'\')" style="font-size:0.75rem;padding:4px 0;border-bottom:1px solid #fee2e2;cursor:pointer;display:flex;justify-content:space-between;"><span>'+typeIcon+' '+(r.clientName||'')+' — '+(r.note||'')+'</span><span style="color:#ef4444;font-weight:600;">'+r.dueDate+'</span></div>';
      }
      if (overdueReminders.length > 5) html += '<div style="font-size:0.7rem;color:var(--gray);text-align:center;padding:4px;">还有 '+(overdueReminders.length-5)+' 条...</div>';
      html += '</div>';
    }
    if (upcomingReminders.length > 0) {
      html += '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px;margin-bottom:10px;">';
      html += '<div style="font-weight:600;font-size:0.85rem;color:#f59e0b;margin-bottom:6px;">📅 近期待跟进</div>';
      for (var i=0; i<upcomingReminders.length; i++) {
        var r = upcomingReminders[i];
        var typeIcon = r.type==='birthday'?'🎂':'⏰';
        var isToday = r.dueDate === today;
        html += '<div onclick="viewClient(\''+r.clientId+'\')" style="font-size:0.75rem;padding:4px 0;border-bottom:1px solid #fef3c7;cursor:pointer;display:flex;justify-content:space-between;"><span>'+typeIcon+' '+(r.clientName||'')+' — '+(r.note||'')+'</span><span style="color:'+(isToday?'#ef4444':'#f59e0b')+';font-weight:600;">'+(isToday?'今天':r.dueDate)+'</span></div>';
      }
      html += '</div>';
    }
    if (recentInteractions.length > 0) {
      html += '<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:10px;margin-bottom:10px;">';
      html += '<div style="font-weight:600;font-size:0.85rem;margin-bottom:6px;">👥 最近客户动态</div>';
      var typeIcons = {meeting:'🤝',call:'📞',wechat:'💬',note:'📝'};
      for (var i=0; i<recentInteractions.length; i++) {
        var inter = recentInteractions[i];
        html += '<div onclick="viewClient(\''+inter.clientId+'\')" style="font-size:0.75rem;padding:4px 0;border-bottom:1px solid #f3f4f6;cursor:pointer;"><span style="color:var(--gray);">'+(inter.date||'')+'</span> <span style="font-weight:600;">'+(inter.clientName||'')+'</span> <span style="font-size:0.7rem;">'+(typeIcons[inter.type]||'📝')+' '+(inter.content||'').slice(0,40)+'</span></div>';
      }
      html += '</div>';
    }
    if (alerts.length > 0) {
      html += '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px;margin-bottom:10px;">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;"><span style="font-weight:600;font-size:0.8rem;">⚠ 持仓预警 ('+alerts.length+'条)</span><span onclick="showAlertConfig()" style="font-size:0.65rem;color:var(--red);cursor:pointer;">⚙ 阈值</span></div>';
      for (var i=0; i<Math.min(alerts.length,5); i++) {
        html += '<div style="font-size:0.7rem;padding:3px 0;border-bottom:1px solid #fef3c7;"><span style="margin-right:4px;">'+alerts[i].icon+'</span>'+alerts[i].text+'</div>';
      }
      html += '</div>';
    }
    var cards = [
      {icon:'👥',title:'客户管理',desc:'画像+推荐+报告',tab:'clients'},
      {icon:'⭐',title:'自选监控',desc:'实时估值+异动',tab:'fund'},
      {icon:'📡',title:'市场行情',desc:'指数/黄金/汇率',tab:'market'},
      {icon:'🤖',title:'AI助手',desc:'DeepSeek+联网',tab:'ai'}
    ];
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">';
    for (var i=0; i<cards.length; i++) {
      html += '<div onclick="switchTab(\''+cards[i].tab+'\')" style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 10px;cursor:pointer;text-align:center;">';
      html += '<div style="font-size:1.5rem;margin-bottom:4px;">'+cards[i].icon+'</div><div style="font-weight:600;font-size:0.82rem;">'+cards[i].title+'</div><div style="font-size:0.65rem;color:var(--gray);">'+cards[i].desc+'</div></div>';
    }
    html += '</div>';
    container.innerHTML = html;
  } catch(e) {
    container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--gray);">⚠️ 加载失败: '+e.message+'<br><button onclick="location.reload()" style="margin-top:12px;padding:8px 16px;background:var(--red);color:#fff;border:none;border-radius:6px;cursor:pointer;">刷新重试</button></div>';
    console.error('renderWorkspace error:', e);
  }
}'''

content = content[:rd_start] + new_workspace + content[rd_end:]
changes.append('3. renderDashboard -> renderWorkspace (today dashboard)')

# ============ 4. Modify viewClient: add briefing button ============
# Add briefing button before edit button
# ============ 4. Modify viewClient: add briefing button ============
# Match the entire edit button element including onclick with +id+
vc_marker = "<button onclick=\"showAddClient(\\''+id+'\\')\" style=\"font-size:0.75rem;padding:4px 10px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;cursor:pointer;\">编辑</button>"
if vc_marker in content:
    vc_replacement = "<button id=\"btnBriefing\" onclick=\"generateMeetingBriefing(\\''+id+'\\')\" style=\"font-size:0.75rem;padding:4px 10px;border:1px solid #bfdbfe;border-radius:6px;background:#eff6ff;color:#1e40af;cursor:pointer;\">📋 会面准备</button><button onclick=\"showAddClient(\\''+id+'\\')\" style=\"font-size:0.75rem;padding:4px 10px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;cursor:pointer;\">编辑</button>"
    content = content.replace(vc_marker, vc_replacement)
    changes.append('4a. Briefing button added to viewClient')
else:
    print('WARNING: viewClient edit button marker not found')

# ============ 4b. Add timeline to viewClient ============
vc_end_marker = "container.innerHTML = html;\n  refreshHoldingPnL(id);"
if vc_end_marker in content:
    content = content.replace(vc_end_marker, "html += renderTimeline(id);\n  container.innerHTML = html;\n  refreshHoldingPnL(id);")
    changes.append('4b. Timeline added to viewClient')
else:
    print('ERROR: viewClient end marker not found'); sys.exit(1)

# ============ 5. Modify renderClientsTab: add tier sorting + badges ============
# Add tier sorting before the for loop
ct_marker = "  else {\n    for (const c of filtered) {"
if ct_marker in content:
    new_ct = "  else {\n    filtered.sort(function(a,b){var to={A:0,B:1,C:2,D:3};var ta=getClientTier(a),tb=getClientTier(b);return (to[ta.tier]||2)-(to[tb.tier]||2);});\n    for (const c of filtered) {\n      const tier = getClientTier(c);"
    content = content.replace(ct_marker, new_ct)
    changes.append('5a. Tier sorting added to renderClientsTab')
else:
    print('WARNING: renderClientsTab sort marker not found')

# Add tier badge after risk level badge in client card
# The risk badge ends with: +(c.riskLevel||'')+'</span></div>';
ct_badge_marker = "+(c.riskLevel||'')+'</span></div>';"
if ct_badge_marker in content:
    content = content.replace(ct_badge_marker, "+(c.riskLevel||'')+'</span><span style=\"font-size:0.6rem;color:'+tier.color+';background:'+tier.bg+';padding:2px 6px;border-radius:4px;margin-left:4px;border:1px solid '+tier.color+'33;\">'+tier.tier+' '+tier.label+'</span></div>';")
    changes.append('5b. Tier badge added to client card')
else:
    print('WARNING: client card badge marker not found')

# ============ 6. Add birthday field to showAddClient ============
sa_marker = "html += fm('标签/备注','<input id=\"cTags\""
if sa_marker in content:
    # Find the end of this line and add birthday after it
    sa_end = content.index(sa_marker)
    # Find the end of this statement (the closing ');)
    line_end = content.index('\n', sa_end)
    birthday_line = "\n  html += fm('生日（选填）','<input id=\"cBirthday\" type=\"date\" value=\"'+(c&&c.birthday?c.birthday:'')+'\" style=\"width:100%;padding:8px;border:1px solid #e5e7eb;border-radius:6px;font-size:0.85rem;\">');"
    content = content[:line_end] + birthday_line + content[line_end:]
    changes.append('6. Birthday field added to showAddClient')
else:
    print('WARNING: showAddClient marker not found')

# ============ 7. Add birthday to saveClient ============
sc_marker = "tags: document.getElementById('cTags').value.trim(),"
if sc_marker in content:
    content = content.replace(sc_marker, "tags: document.getElementById('cTags').value.trim(), birthday: (document.getElementById('cBirthday')||{}).value||'',")
    changes.append('7. Birthday field added to saveClient')
else:
    print('WARNING: saveClient marker not found')

# ============ 8. Update switchTab ============
st_marker = "if (tab === 'dashboard') renderDashboard();"
if st_marker in content:
    content = content.replace(st_marker, "if (tab === 'dashboard') renderWorkspace();")
    changes.append('8. switchTab updated')
else:
    print('WARNING: switchTab marker not found')

# ============ 9. Update DOMContentLoaded ============
dc_marker = "setTimeout(function() { renderDashboard(); }, 300);"
if dc_marker in content:
    content = content.replace(dc_marker, "setTimeout(function() { renderWorkspace(); }, 300);")
    changes.append('9. DOMContentLoaded updated')
else:
    print('WARNING: DOMContentLoaded marker not found')

# ============ Write output ============
with open('index.html', 'w') as f:
    f.write(content)

print('=== v3.0 upgrade complete ===')
for c in changes:
    print('  ✓', c)
print('Total changes:', len(changes))
