const fileInput = document.getElementById('fileInput');
const previewImage = document.getElementById('previewImage');
const uploadBtn = document.getElementById('uploadBtn');
const statusText = document.getElementById('statusText');
const resultBox = document.getElementById('resultBox');

fileInput.addEventListener('change', () => {
  const file = fileInput.files?.[0];
  if (!file) {
    previewImage.classList.add('hidden');
    previewImage.src = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImage.src = e.target?.result;
    previewImage.classList.remove('hidden');
  };
  reader.readAsDataURL(file);
});

uploadBtn.addEventListener('click', async () => {
  const file = fileInput.files?.[0];
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
  } catch (error) {
    console.error(error);
    setStatus('网络异常，请检查服务器连接', true);
  } finally {
    uploadBtn.disabled = false;
  }
});

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

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
