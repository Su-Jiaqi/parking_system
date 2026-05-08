const cameraBtn = document.getElementById('cameraBtn');
const galleryBtn = document.getElementById('galleryBtn');
const cameraInput = document.getElementById('cameraInput');
const galleryInput = document.getElementById('galleryInput');
const previewImage = document.getElementById('previewImage');
const selectedFileText = document.getElementById('selectedFileText');
const uploadBtn = document.getElementById('uploadBtn');
const refreshRecordsBtn = document.getElementById('refreshRecordsBtn');
const statusText = document.getElementById('statusText');
const resultBox = document.getElementById('resultBox');
const recordsBox = document.getElementById('recordsBox');

let selectedFile = null;

cameraBtn.addEventListener('click', () => {
  cameraInput.click();
});

galleryBtn.addEventListener('click', () => {
  galleryInput.click();
});

cameraInput.addEventListener('change', () => {
  handleFileSelected(cameraInput.files?.[0], '拍照图片');
  galleryInput.value = '';
});

galleryInput.addEventListener('change', () => {
  handleFileSelected(galleryInput.files?.[0], '相册图片');
  cameraInput.value = '';
});

uploadBtn.addEventListener('click', async () => {
  const file = selectedFile;
  if (!file) {
    setStatus('请先选择车牌图片', true);
    return;
  }

  const action = document.querySelector('input[name="action"]:checked')?.value;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('action', action);

  setStatus('正在上传并识别，请稍候...', false);
  uploadBtn.disabled = true;

  try {
    const response = await fetch('/api/parking/upload', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
      setStatus(data.message || '处理失败', true);
      renderResult(data, false);
      return;
    }

    setStatus(data.message || '处理成功', false);
    renderResult(data, true);
    await loadRecords();
  } catch (error) {
    console.error(error);
    setStatus('网络异常，请检查服务器连接', true);
  } finally {
    uploadBtn.disabled = false;
  }
});

refreshRecordsBtn.addEventListener('click', () => {
  loadRecords();
});

function handleFileSelected(file, sourceLabel) {
  selectedFile = file ?? null;

  if (!file) {
    previewImage.classList.add('hidden');
    previewImage.src = '';
    selectedFileText.textContent = '当前未选择图片';
    return;
  }

  selectedFileText.textContent = `已选择${sourceLabel}：${file.name}`;
  const reader = new FileReader();
  reader.onload = (event) => {
    previewImage.src = event.target?.result;
    previewImage.classList.remove('hidden');
  };
  reader.readAsDataURL(file);
}

function setStatus(message, isError) {
  statusText.textContent = message;
  statusText.className = isError ? 'status error' : 'status success';
}

function renderResult(data, success) {
  if (!success) {
    resultBox.className = 'result-box';
    resultBox.innerHTML = `
      <div><strong>处理状态：</strong>失败</div>
      <div><strong>错误信息：</strong>${escapeHtml(data.message || '未知错误')}</div>
    `;
    return;
  }

  resultBox.className = 'result-box';
  resultBox.innerHTML = `
    <div><strong>处理状态：</strong>成功</div>
    <div><strong>车牌号：</strong>${escapeHtml(data.plate_number || '')}</div>
    <div><strong>操作：</strong>${data.action === 'entry' ? '入场' : '出场'}</div>
    <div><strong>提示：</strong>${escapeHtml(data.message || '')}</div>
    <div><strong>入场时间：</strong>${escapeHtml(data.entry_time || '-')}</div>
    <div><strong>出场时间：</strong>${escapeHtml(data.exit_time || '-')}</div>
    <div><strong>停车时长：</strong>${data.duration_minutes ?? '-'} 分钟</div>
    <div><strong>停车费用：</strong>${data.fee ?? '-'} 元</div>
  `;
}

async function loadRecords() {
  recordsBox.className = 'result-box empty';
  recordsBox.textContent = '正在加载记录...';

  try {
    const response = await fetch('/api/parking/records');
    const data = await response.json();

    if (!response.ok || !data.success) {
      recordsBox.textContent = data.message || '加载记录失败';
      return;
    }

    renderRecords(data.records || []);
  } catch (error) {
    console.error(error);
    recordsBox.textContent = '加载记录失败，请检查网络连接';
  }
}

function renderRecords(records) {
  if (!records.length) {
    recordsBox.className = 'result-box empty';
    recordsBox.textContent = '暂无停车记录';
    return;
  }

  recordsBox.className = 'records-list';
  recordsBox.innerHTML = records
    .map(
      (record) => `
        <div class="record-item">
          <div><strong>车牌号：</strong>${escapeHtml(record.plate_number || '')}</div>
          <div><strong>状态：</strong>${record.status === 'IN' ? '在场' : '已离场'}</div>
          <div><strong>入场时间：</strong>${escapeHtml(record.entry_time || '-')}</div>
          <div><strong>出场时间：</strong>${escapeHtml(record.exit_time || '-')}</div>
          <div><strong>停车时长：</strong>${record.duration_minutes ?? '-'} 分钟</div>
          <div><strong>费用：</strong>${record.fee ?? '-'} 元</div>
        </div>
      `
    )
    .join('');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

loadRecords();
