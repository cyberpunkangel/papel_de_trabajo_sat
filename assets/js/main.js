// Funciones principales de la aplicación
const DOWNLOADS_VIEWER_DEFAULT_URL = '/api/downloads/browse';
const PAPERWORKS_VIEWER_DEFAULT_URL = '/api/reports/browse';
const PACKAGES_ENDPOINTS = {
    periods: '/api/packages/periods',
    generate: '/api/packages/generate'
};
const TABULADOR_COLUMNS = [
    { key: 'lower_limit', placeholder: '0.00', required: true },
    { key: 'upper_limit', placeholder: '0.00', required: false },
    { key: 'fixed_fee', placeholder: '0.00', required: true },
    { key: 'rate', placeholder: '0.00%', required: true }
];
const TABULADOR_INITIAL_ROWS = 11;
const TABULADOR_ENDPOINTS = {
    save: '/api/tabulador',
    check: '/api/tabulador'
};

const TABULADOR_COLUMN_TOOLTIPS = {
    lower_limit: 'Monto mínimo del rango al que aplica la tasa.',
    upper_limit: 'Monto máximo del rango. Puedes usar "En adelante" en el último renglón.',
    fixed_fee: 'Cuota fija del rango según el tabulador oficial SAT.',
    rate: 'Porcentaje marginal que aplica al excedente del límite inferior.',
};

const FORM_FIELD_TOOLTIPS = {
    '#cert-file': 'Selecciona el certificado público de tu e.firma con extensión .cer.',
    '#key-file': 'Selecciona la llave privada de tu e.firma con extensión .key.',
    '#password': 'Captura la contraseña de la llave privada (.key).',
    '#show-password': 'Muestra u oculta la contraseña de la e.firma.',
    'input[name="tipo_descarga"][value="anio_completo"]': 'Consulta todos los documentos del ejercicio fiscal seleccionado.',
    'input[name="tipo_descarga"][value="mes_especifico"]': 'Consulta solo un mes del ejercicio; suele ser más estable con SAT.',
    'input[name="tipo_descarga"][value="rango_personalizado"]': 'Permite definir fechas exactas de inicio y fin para la consulta.',
    '#anio_fiscal': 'Año fiscal que se usará para la descarga de XML.',
    '#mes': 'Mes específico a consultar cuando eliges descarga mensual.',
    '#fecha_inicio': 'Fecha y hora inicial del rango personalizado (incluye segundos).',
    '#fecha_fin': 'Fecha y hora final del rango personalizado (incluye segundos).',
    '#filter_fecha_pago': 'Filtra nómina por FechaPago para conservar solo XML del periodo elegido.',
    'input[name="doc_nomina"]': 'Incluye recibos de nómina (ingresos por salarios).',
    'input[name="doc_retenciones"]': 'Incluye constancias de retenciones (intereses, dividendos, etc.).',
    'input[name="doc_ingresos"]': 'Incluye otros CFDI recibidos; puede traer XML no deducibles.',
    'input[name="document_status"][value="active"]': 'Descarga únicamente comprobantes vigentes.',
    'input[name="document_status"][value="cancelled"]': 'Descarga únicamente comprobantes cancelados.',
    'input[name="document_status"][value="both"]': 'Descarga vigentes y cancelados en procesos separados.',
    '#fiel_password_download': 'Contraseña de la llave privada para autenticar la descarga SAT.',
    '#show-password-download': 'Muestra u oculta la contraseña capturada para descargar.',
    '#report-periodo': 'Ejercicio que se tomará para procesar XML y generar el papel de trabajo.',
    '#tabulador-add-row': 'Agrega una fila al tabulador ISR.',
    '#tabulador-delete-row': 'Elimina la última fila del tabulador ISR.',
    '#tabulador-clear': 'Limpia los valores capturados en todas las filas del tabulador.',
    '#tabulador-save': 'Guarda el tabulador ISR capturado para el ejercicio seleccionado.',
    '#btn-generar-reporte': 'Genera el papel de trabajo en Excel con la información procesada.',
    '#nombre': 'Nombre completo del contribuyente tal como aparece en su identificación.',
    '#rfc': 'RFC del contribuyente (12 o 13 caracteres según corresponda).',
    '#curp': 'CURP del contribuyente (18 caracteres).',
    '#packages-periodo': 'Ejercicio elegible para preparar paquetes ZIP de carga SAT.',
    '#btn-generar-paquetes': 'Genera los paquetes ZIP de hasta 4 MB por tipo de documento.',
};

const tabuladorState = {
    isDirty: false,
    hasSavedSnapshot: false,
    lastSavedAt: null,
    isLoading: false,
    currentPeriod: '',
};

const EMPTY_TABULADOR_ERROR_TEXT = 'Debes capturar al menos una fila completa del tabulador ISR para generar el papel de trabajo.';

function getReportPeriodValue() {
    const selector = document.getElementById('report-periodo');
    return selector ? selector.value : '';
}

function normalizePeriodString(value) {
    const trimmed = (value || '').trim();
    if (!trimmed) {
        return '';
    }
    const digitsOnly = trimmed.replace(/[^0-9]/g, '');
    return digitsOnly.length === 4 ? digitsOnly : '';
}

function getTabuladorPeriod() {
    return normalizePeriodString(getReportPeriodValue());
}

function setActiveTabuladorPeriod(periodo) {
    const normalized = normalizePeriodString(periodo);
    if (!normalized) {
        return;
    }
    tabuladorState.currentPeriod = normalized;
    setReportPeriodValue(normalized);
    updateGenerateButtonAvailability();
}

// Abrir modal
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Si es el modal de descarga, cargar info de FIEL
        if (modalId === 'download-modal') {
            loadFielInfo();
        } else if (modalId === 'report-modal') {
            loadSavedTabuladorData({ period: getTabuladorPeriod() });
        } else if (modalId === 'packages-modal') {
            loadEligiblePackagePeriods();
        }
    }
}

// Cerrar modal
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

// Cerrar modal al hacer click fuera
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

// Manejo de archivos
function handleFileSelect(inputId, displayId) {
    const input = document.getElementById(inputId);
    const display = document.getElementById(displayId);
    
    if (input && input.files.length > 0) {
        display.textContent = input.files[0].name;
        display.style.color = 'var(--success-color)';
    } else {
        display.textContent = 'Ningún archivo seleccionado';
        display.style.color = 'var(--text-muted)';
    }
}

function addOneCalendarYear(dateValue) {
    const limitDate = new Date(dateValue.getTime());
    const originalMonth = limitDate.getMonth();

    limitDate.setFullYear(limitDate.getFullYear() + 1);

    // Ajuste para fechas como 29/feb en años no bisiestos
    if (limitDate.getMonth() !== originalMonth) {
        limitDate.setDate(0);
    }

    return limitDate;
}

// Mostrar/Ocultar contraseña
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Mostrar alerta
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.style.whiteSpace = 'pre-line';
    alertDiv.textContent = message;

    // Buscar contenedor dedicado primero (ej. fiel-alert-container), si no usar el modal body
    const dedicated = document.querySelector('.modal.active #fiel-alert-container');
    const container = dedicated || document.querySelector('.modal.active .modal-body');

    if (container) {
        // Limpiar alertas anteriores
        container.querySelectorAll('.alert').forEach(el => el.remove());

        container.appendChild(alertDiv);

        // Scroll para que sea visible
        alertDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Solo auto-cerrar mensajes de exito, los errores permanecen visibles
        if (type === 'success') {
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    }
}

// Validar formulario FIEL
function validateFielForm() {
    const certFile = document.getElementById('cert-file').files[0];
    const keyFile = document.getElementById('key-file').files[0];
    const password = document.getElementById('password').value;
    
    if (!certFile) {
        showAlert('Por favor selecciona el archivo de certificado (.cer)', 'error');
        return false;
    }
    
    if (!keyFile) {
        showAlert('Por favor selecciona el archivo de llave privada (.key)', 'error');
        return false;
    }
    
    if (!password) {
        showAlert('Por favor ingresa la contraseña', 'error');
        return false;
    }
    
    return true;
}

// Guardar configuración FIEL
async function saveFielConfig(event) {
    event.preventDefault();

    if (!validateFielForm()) {
        return;
    }

    const formData = new FormData();
    formData.append('cert_file', document.getElementById('cert-file').files[0]);
    formData.append('key_file', document.getElementById('key-file').files[0]);
    formData.append('password', document.getElementById('password').value);

    // Mostrar spinner
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<div class="spinner"></div> Validando...';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/fiel/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showAlert(
                `Configuracion validada y guardada exitosamente\n\nRFC: ${result.data.rfc}\nNombre: ${result.data.nombre}\nValido hasta: ${result.data.valido_hasta}\nSerial: ${result.data.serial}`,
                'success'
            );

            // Cerrar modal después de 3 segundos para que alcance a leer
            setTimeout(() => {
                closeModal('fiel-modal');
                location.reload();
            }, 3000);
        } else {
            const msg = result.message || 'Error desconocido al validar la FIEL';
            showAlert(`Error: ${msg}`, 'error');
        }
    } catch (error) {
        showAlert(`Error de conexion con el servidor: ${error.message}`, 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Verificar estado de configuración al cargar
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si existe configuración FIEL
    fetch('/api/fiel/status')
        .then(response => response.json())
        .then(data => {
            if (data.has_config) {
                // Mostrar indicador de configuración activa
                const fielCard = document.querySelector('.card:first-child');
                if (fielCard) {
                    const indicator = document.createElement('div');
                    indicator.className = 'alert-success';
                    indicator.style.marginBottom = '15px';
                    indicator.innerHTML = `✅ Configurado para RFC: ${data.rfc}`;
                    fielCard.querySelector('.card-description').after(indicator);
                }
            }
        })
        .catch(error => console.error('Error checking config:', error));
    
    // Verificar si existen datos del contribuyente
    fetch('/api/contribuyente')
        .then(response => response.json())
        .then(data => {
            if (data.has_data) {
                // Mostrar indicador de datos guardados
                const contribCard = document.querySelector('.card:nth-child(3)');
                if (contribCard) {
                    const indicator = document.createElement('div');
                    indicator.className = 'alert-success';
                    indicator.style.marginBottom = '15px';
                    indicator.innerHTML = `✅ ${data.nombre} (${data.rfc})`;
                    contribCard.querySelector('.card-description').after(indicator);
                }
                
                window.contribuyenteData = data;
                // Cargar datos en el formulario cuando se abra el modal
                loadContribuyenteData(data);
            }
        })
        .catch(error => console.error('Error checking contribuyente:', error));

    initializeVerDescargasButton();
    initializeTabuladorForm();
    initializeReportGenerator();
    initializePackagesGenerator();
    initializeReportPeriodSync();
    loadSavedTabuladorData({ force: true, period: getTabuladorPeriod() });
    initializeFieldTooltips();
});

function initializeFieldTooltips() {
    Object.entries(FORM_FIELD_TOOLTIPS).forEach(([selector, tooltip]) => {
        document.querySelectorAll(selector).forEach(element => {
            if (!element) {
                return;
            }
            element.setAttribute('title', tooltip);
        });
    });

    applyTabuladorInputTooltips();
    initializeFieldHelpIcons();
}

function appendHelpIcon(targetElement, tooltip) {
    if (!targetElement || !tooltip) {
        return;
    }

    const existingIcon = targetElement.querySelector('.field-help-icon');
    if (existingIcon) {
        existingIcon.setAttribute('title', tooltip);
        existingIcon.setAttribute('aria-label', tooltip);
        return;
    }

    const icon = document.createElement('span');
    icon.className = 'field-help-icon';
    icon.textContent = 'ⓘ';
    icon.setAttribute('title', tooltip);
    icon.setAttribute('aria-label', tooltip);
    targetElement.appendChild(icon);
}

function initializeFieldHelpIcons() {
    document.querySelectorAll('label[for]').forEach(label => {
        const inputId = label.getAttribute('for');
        if (!inputId) {
            return;
        }
        const input = document.getElementById(inputId);
        if (!input) {
            return;
        }
        const tooltip = input.getAttribute('title') || '';
        appendHelpIcon(label, tooltip);
    });

    document.querySelectorAll('.radio-option, .checkbox-option').forEach(option => {
        const input = option.querySelector('input');
        const textContainer = option.querySelector('span');
        if (!input || !textContainer) {
            return;
        }
        const tooltip = input.getAttribute('title') || '';
        appendHelpIcon(textContainer, tooltip);
    });

    const tabHeaders = document.querySelectorAll('#tabulador-table thead th');
    tabHeaders.forEach((header, index) => {
        const column = TABULADOR_COLUMNS[index];
        if (!column) {
            return;
        }
        const tooltip = TABULADOR_COLUMN_TOOLTIPS[column.key] || '';
        header.setAttribute('title', tooltip);
        appendHelpIcon(header, tooltip);
    });
}

function applyTabuladorInputTooltips() {
    document.querySelectorAll('.tabulador-input').forEach(input => {
        const columnKey = input.dataset.columnKey;
        const tooltip = TABULADOR_COLUMN_TOOLTIPS[columnKey] || 'Campo del tabulador ISR.';
        input.setAttribute('title', tooltip);
    });
}

function initializeVerDescargasButton() {
    const button = document.getElementById('ver-descargas-btn');
    if (!button) {
        return;
    }

    setVerDescargasButtonState(false, DOWNLOADS_VIEWER_DEFAULT_URL, button);

    button.addEventListener('click', function(event) {
        if (button.classList.contains('btn-disabled')) {
            event.preventDefault();
        }
    });

    refreshVerDescargasButtonState();
}

function setVerDescargasButtonState(enabled, url = DOWNLOADS_VIEWER_DEFAULT_URL, button) {
    const target = button || document.getElementById('ver-descargas-btn');
    if (!target) {
        return;
    }

    target.href = url || DOWNLOADS_VIEWER_DEFAULT_URL;

    if (enabled) {
        target.classList.remove('btn-disabled');
        target.classList.remove('btn-secondary');
        target.classList.add('btn-success');
        target.setAttribute('aria-disabled', 'false');
        target.removeAttribute('tabindex');
        target.title = 'Abrir archivos descargados';
    } else {
        target.classList.add('btn-disabled');
        target.classList.add('btn-secondary');
        target.classList.remove('btn-success');
        target.setAttribute('aria-disabled', 'true');
        target.setAttribute('tabindex', '-1');
        target.title = 'Aún no hay descargas disponibles';
    }
}

async function refreshVerDescargasButtonState() {
    const button = document.getElementById('ver-descargas-btn');
    if (!button) {
        return;
    }

    try {
        const response = await fetch('/api/downloads/status');
        if (!response.ok) {
            throw new Error('Estado HTTP ' + response.status);
        }
        const data = await response.json();
        const hasDownloads = Boolean(data.has_downloads);
        const viewerUrl = data.viewer_url || DOWNLOADS_VIEWER_DEFAULT_URL;
        setVerDescargasButtonState(hasDownloads, viewerUrl, button);
    } catch (error) {
        console.error('Error checking downloads:', error);
        setVerDescargasButtonState(false, DOWNLOADS_VIEWER_DEFAULT_URL, button);
    }
}

function initializeReportGenerator() {
    const generateBtn = document.getElementById('btn-generar-reporte');
    if (generateBtn) {
        generateBtn.addEventListener('click', generarReporte);
    }

    const reportLinks = [
        document.getElementById('ver-reporte-btn'),
        document.getElementById('modal-report-download')
    ];
    reportLinks.forEach(link => {
        if (!link) {
            return;
        }
        link.addEventListener('click', event => {
            if (link.classList.contains('btn-disabled')) {
                event.preventDefault();
            }
        });
    });

    refreshReportStatus();
}

function initializeReportPeriodSync() {
    const selector = document.getElementById('report-periodo');
    if (!selector) {
        return;
    }

    selector.addEventListener('change', () => {
        const selectedPeriod = getTabuladorPeriod();
        if (!selectedPeriod) {
            return;
        }

        if (tabuladorState.isDirty) {
            const revertValue = tabuladorState.currentPeriod || selectedPeriod;
            if (revertValue && revertValue !== selectedPeriod) {
                selector.value = revertValue;
            }
            updateTabuladorSaveStatus('Guarda o limpia el tabulador ISR antes de cambiar de ejercicio.', 'warning');
            return;
        }

        loadSavedTabuladorData({ period: selectedPeriod });
    });
}

function setReportLinkState(enabled, url = PAPERWORKS_VIEWER_DEFAULT_URL, ...links) {
    links.filter(Boolean).forEach(link => {
        if (!link) return;
        link.href = enabled && url ? url : '#';
        if (enabled) {
            link.classList.remove('btn-disabled');
            link.classList.remove('btn-secondary');
            link.classList.add('btn-success');
            link.setAttribute('aria-disabled', 'false');
            link.removeAttribute('tabindex');
            link.title = 'Abrir papeles de trabajo generados';
        } else {
            link.classList.add('btn-disabled');
            link.classList.add('btn-secondary');
            link.classList.remove('btn-success');
            link.setAttribute('aria-disabled', 'true');
            link.setAttribute('tabindex', '-1');
            link.title = 'Aún no hay papeles de trabajo generados';
        }
    });
}

function setReportStatusMessage(text, tone = 'info') {
    const message = document.getElementById('report-status-message');
    if (!message) {
        return;
    }
    message.textContent = text;
    message.classList.remove('success', 'error');
    if (tone !== 'info') {
        message.classList.add(tone);
    }
}

async function refreshReportStatus() {
    const modalLink = document.getElementById('modal-report-download');
    const cardLink = document.getElementById('ver-reporte-btn');

    try {
        const response = await fetch('/api/reports/status');
        if (!response.ok) {
            throw new Error('HTTP ' + response.status);
        }
        const data = await response.json();
        if (data.success && data.has_report && data.report) {
            const infoText = `Último papel de trabajo: ${data.report.filename} (${data.report.generated_display})`;
            const viewerUrl = data.viewer_url || data.report.viewer_url || PAPERWORKS_VIEWER_DEFAULT_URL;
            setReportStatusMessage(infoText, 'success');
            setReportLinkState(true, viewerUrl, modalLink, cardLink);
        } else {
            setReportStatusMessage('Aún no hay papeles de trabajo generados.');
            setReportLinkState(false, '#', modalLink, cardLink);
        }
    } catch (error) {
        console.error('Error checking report status:', error);
        setReportStatusMessage('No se pudo verificar el estado del papel de trabajo.', 'error');
        setReportLinkState(false, '#', modalLink, cardLink);
    }
}

function initializePackagesGenerator() {
    const openFolderLink = document.getElementById('packages-open-folder');
    if (!openFolderLink) {
        return;
    }

    openFolderLink.addEventListener('click', event => {
        if (openFolderLink.classList.contains('btn-disabled')) {
            event.preventDefault();
        }
    });
}

function setPackagesStatusMessage(message, tone = 'info') {
    const statusElement = document.getElementById('packages-status-message');
    if (!statusElement) {
        return;
    }
    statusElement.textContent = message;
    statusElement.classList.remove('success', 'error');
    if (tone !== 'info') {
        statusElement.classList.add(tone);
    }
}

function setPackagesOpenFolderState(enabled, url = '#') {
    const link = document.getElementById('packages-open-folder');
    if (!link) {
        return;
    }

    link.href = enabled ? url : '#';
    if (enabled) {
        link.classList.remove('btn-disabled');
        link.classList.remove('btn-secondary');
        link.classList.add('btn-success');
        link.setAttribute('aria-disabled', 'false');
        link.removeAttribute('tabindex');
        link.title = 'Abrir carpeta con los paquetes generados';
    } else {
        link.classList.add('btn-disabled');
        link.classList.add('btn-secondary');
        link.classList.remove('btn-success');
        link.setAttribute('aria-disabled', 'true');
        link.setAttribute('tabindex', '-1');
        link.title = 'Aún no hay paquetes generados';
    }
}

function setGeneratePackagesButtonEnabled(enabled, loadingText = '') {
    const button = document.getElementById('btn-generar-paquetes');
    if (!button) {
        return;
    }

    if (!button.dataset.originalText) {
        button.dataset.originalText = button.innerHTML;
    }

    button.disabled = !enabled;
    button.innerHTML = enabled
        ? button.dataset.originalText
        : (loadingText || '⏳ Generando...');
}

async function loadEligiblePackagePeriods() {
    const periodSelect = document.getElementById('packages-periodo');
    const resultsBox = document.getElementById('packages-results');
    if (!periodSelect) {
        return;
    }

    periodSelect.disabled = true;
    periodSelect.innerHTML = '<option value="">Cargando ejercicios elegibles...</option>';
    setGeneratePackagesButtonEnabled(false, '⏳ Cargando...');
    setPackagesOpenFolderState(false);

    if (resultsBox) {
        resultsBox.style.display = 'none';
        resultsBox.innerHTML = '';
    }

    try {
        const response = await fetch(PACKAGES_ENDPOINTS.periods);
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || 'No se pudieron cargar los ejercicios elegibles.');
        }

        periodSelect.innerHTML = '';
        const periods = Array.isArray(data.periods) ? data.periods : [];

        if (!periods.length) {
            periodSelect.innerHTML = '<option value="">No hay ejercicios elegibles</option>';
            periodSelect.disabled = true;
            setGeneratePackagesButtonEnabled(false);
            setPackagesStatusMessage(
                'No hay ejercicios elegibles. Verifica XML vigentes en las 3 carpetas y papel de trabajo del mismo año.',
                'error'
            );
            return;
        }

        periods.forEach(item => {
            const option = document.createElement('option');
            option.value = item.period;
            option.textContent = `Ejercicio ${item.period} (${item.total_xml} XML)`;
            periodSelect.appendChild(option);
        });

        periodSelect.disabled = false;
        setGeneratePackagesButtonEnabled(true);
        setPackagesStatusMessage(`Selecciona un ejercicio y genera los ZIPs (límite: 4 MB por archivo).`);
    } catch (error) {
        console.error('Error loading package periods:', error);
        periodSelect.innerHTML = '<option value="">Error al cargar ejercicios</option>';
        periodSelect.disabled = true;
        setGeneratePackagesButtonEnabled(false);
        setPackagesStatusMessage(
            error instanceof Error ? error.message : 'No se pudieron cargar los ejercicios elegibles.',
            'error'
        );
    }
}

function renderGeneratedPackages(data) {
    const resultsBox = document.getElementById('packages-results');
    if (!resultsBox) {
        return;
    }

    const packages = Array.isArray(data.packages) ? data.packages : [];
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    if (!packages.length) {
        if (warnings.length) {
            resultsBox.innerHTML = `<p class="warning">⚠️ ${warnings.join(' ')}</p>`;
            resultsBox.style.display = 'block';
        } else {
            resultsBox.style.display = 'none';
            resultsBox.innerHTML = '';
        }
        return;
    }

    let html = '<p><strong>ZIPs generados:</strong></p><ul style="margin: 8px 0 0 18px; line-height: 1.55;">';
    packages.forEach(item => {
        const name = item.name || 'Archivo.zip';
        const size = item.size_human || '---';
        const filesCount = Number(item.files_count || 0);
        const downloadUrl = item.download_url || '#';
        const openUrl = item.open_url || '#';
        html += `
            <li>
                <strong>${name}</strong> (${size}, ${filesCount} archivo(s)) -
                <a href="${downloadUrl}">Descargar</a> |
                <a href="${openUrl}">Abrir ubicación</a>
            </li>`;
    });
    html += '</ul>';

    if (warnings.length) {
        html += `<p class="warning" style="margin-top: 10px;">⚠️ ${warnings.join(' ')}</p>`;
    }

    resultsBox.innerHTML = html;
    resultsBox.style.display = 'block';
}

async function generateSatPackages(event) {
    if (event) {
        event.preventDefault();
    }

    const periodSelect = document.getElementById('packages-periodo');
    if (!periodSelect) {
        return;
    }

    const selectedPeriod = periodSelect.value;
    if (!selectedPeriod) {
        setPackagesStatusMessage('Selecciona un ejercicio elegible para generar paquetes.', 'error');
        return;
    }

    periodSelect.disabled = true;
    setGeneratePackagesButtonEnabled(false, '⏳ Generando...');
    setPackagesStatusMessage('Generando paquetes ZIP, espera unos segundos...');

    try {
        const formData = new FormData();
        formData.append('periodo', selectedPeriod);

        const response = await fetch(PACKAGES_ENDPOINTS.generate, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || 'No se pudieron generar los paquetes ZIP.');
        }

        const periodLabel = data.period ? ` del ejercicio ${data.period}` : '';
        setPackagesStatusMessage(`Paquetes ZIP generados correctamente${periodLabel}.`, 'success');
        setPackagesOpenFolderState(Boolean(data.folder_open_url), data.folder_open_url || '#');
        renderGeneratedPackages(data);
    } catch (error) {
        console.error('Error generating SAT packages:', error);
        setPackagesStatusMessage(
            error instanceof Error ? error.message : 'No se pudieron generar los paquetes ZIP.',
            'error'
        );
    } finally {
        periodSelect.disabled = false;
        setGeneratePackagesButtonEnabled(true);
    }
}

function getTabuladorTableBody() {
    const table = document.getElementById('tabulador-table');
    return table ? table.querySelector('tbody') : null;
}

function resetTabuladorTable(rows = []) {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }
    tbody.innerHTML = '';
    const totalRows = Math.max(rows.length, TABULADOR_INITIAL_ROWS);
    for (let i = 0; i < totalRows; i += 1) {
        addTabuladorRow(rows[i] || {});
    }
}

function formatTabuladorValueForInput(columnKey, rawValue) {
    if (rawValue === null || rawValue === undefined) {
        return '';
    }

    if (typeof rawValue === 'string') {
        return rawValue;
    }

    if (columnKey === 'rate') {
        const numericRate = Number(rawValue);
        if (!Number.isFinite(numericRate)) {
            return '';
        }
        const percentValue = numericRate <= 1 ? numericRate * 100 : numericRate;
        return `${formatNumberForDisplay(percentValue, 4)}%`;
    }

    if (typeof rawValue === 'number') {
        return formatNumberForDisplay(rawValue);
    }

    return String(rawValue);
}

function formatNumberForDisplay(value, decimals = 2) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return '';
    }
    return numeric.toFixed(decimals);
}

function initializeTabuladorForm() {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }

    resetTabuladorTable();
    updateTabuladorSaveStatus('Aún no guardas un tabulador ISR.', 'info');

    tbody.addEventListener('paste', handleTabuladorPaste);
    tbody.addEventListener('input', handleTabuladorInputChange);

    const addButton = document.getElementById('tabulador-add-row');
    if (addButton) {
        addButton.addEventListener('click', () => {
            addTabuladorRow();
            markTabuladorDirty();
        });
    }

    const deleteButton = document.getElementById('tabulador-delete-row');
    if (deleteButton) {
        deleteButton.addEventListener('click', removeTabuladorLastRow);
    }

    const clearButton = document.getElementById('tabulador-clear');
    if (clearButton) {
        clearButton.addEventListener('click', clearTabuladorRows);
    }

    const saveButton = document.getElementById('tabulador-save');
    if (saveButton) {
        saveButton.addEventListener('click', handleTabuladorSave);
    }

    updateGenerateButtonAvailability();
}

function handleTabuladorInputChange(event) {
    if (!event.target.classList.contains('tabulador-input')) {
        return;
    }
    markTabuladorDirty();
    clearEmptyTabuladorErrorIfRecovered();
    updateGenerateButtonAvailability();
}

function addTabuladorRow(values = {}) {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }

    const row = document.createElement('tr');
    TABULADOR_COLUMNS.forEach((column, index) => {
        const cell = document.createElement('td');
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = column.placeholder;
        input.className = 'tabulador-input';
        input.dataset.columnKey = column.key;
        input.dataset.colIndex = String(index);
        input.title = TABULADOR_COLUMN_TOOLTIPS[column.key] || 'Campo del tabulador ISR.';
        const displayValue = formatTabuladorValueForInput(column.key, values[column.key]);
        input.value = displayValue || '';
        cell.appendChild(input);
        row.appendChild(cell);
    });

    tbody.appendChild(row);
}

function removeTabuladorLastRow() {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }

    const rows = tbody.querySelectorAll('tr');
    if (rows.length <= 1) {
        updateTabuladorSaveStatus('Debe existir al menos una fila en el tabulador.', 'warning');
        return;
    }

    rows[rows.length - 1].remove();
    markTabuladorDirty();
    setTabuladorError('');
    updateGenerateButtonAvailability();
}

function clearTabuladorRows() {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }
    tbody.querySelectorAll('.tabulador-input').forEach(input => {
        input.value = '';
    });
    markTabuladorDirty();
    setTabuladorError('');
    updateGenerateButtonAvailability();
}

function ensureTabuladorRowCount(expectedCount) {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }
    while (tbody.children.length < expectedCount) {
        addTabuladorRow();
    }
}

function collectTabuladorData() {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return [];
    }

    const rows = [];
    tbody.querySelectorAll('tr').forEach(row => {
        const rowData = {};
        let requiredComplete = true;
        let hasValue = false;
        TABULADOR_COLUMNS.forEach(column => {
            const input = row.querySelector(`.tabulador-input[data-column-key="${column.key}"]`);
            const value = input ? input.value.trim() : '';
            if (value) {
                hasValue = true;
            } else if (column.required !== false) {
                requiredComplete = false;
            }
            rowData[column.key] = value;
        });
        if (hasValue && requiredComplete) {
            rows.push(rowData);
        }
    });
    return rows;
}

function getTabuladorIncompleteRowsCount() {
    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return 0;
    }

    let incompleteRows = 0;
    tbody.querySelectorAll('tr').forEach(row => {
        let hasAnyValue = false;
        let hasAllRequired = true;

        TABULADOR_COLUMNS.forEach(column => {
            const input = row.querySelector(`.tabulador-input[data-column-key="${column.key}"]`);
            const value = input ? input.value.trim() : '';

            if (value) {
                hasAnyValue = true;
            } else if (column.required !== false) {
                hasAllRequired = false;
            }
        });

        if (hasAnyValue && !hasAllRequired) {
            incompleteRows += 1;
        }
    });

    return incompleteRows;
}

function validateReportGenerationInputs() {
    const errors = [];
    const tabuladorPeriod = getTabuladorPeriod();
    const completeRows = collectTabuladorData().length;
    const incompleteRows = getTabuladorIncompleteRowsCount();

    if (!tabuladorPeriod) {
        errors.push('Selecciona el ejercicio a procesar antes de generar el papel de trabajo.');
    }

    if (completeRows === 0) {
        if (incompleteRows > 0) {
            errors.push('Hay filas incompletas en el tabulador ISR. Complétalas o límpialas antes de generar.');
        } else {
            errors.push('Debes capturar al menos una fila completa del tabulador ISR para generar el papel de trabajo.');
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        tabuladorPeriod,
        completeRows,
        incompleteRows,
    };
}

function clearEmptyTabuladorErrorIfRecovered() {
    const completeRows = collectTabuladorData().length;
    if (completeRows <= 0) {
        return;
    }

    const tabuladorErrorElement = document.getElementById('tabulador-error');
    if (tabuladorErrorElement && tabuladorErrorElement.style.display !== 'none') {
        const currentError = (tabuladorErrorElement.textContent || '').trim();
        if (currentError.includes(EMPTY_TABULADOR_ERROR_TEXT)) {
            setTabuladorError('');
        }
    }

    const reportStatusElement = document.getElementById('report-status-message');
    if (reportStatusElement && reportStatusElement.classList.contains('error')) {
        const currentStatus = (reportStatusElement.textContent || '').trim();
        if (currentStatus.includes(EMPTY_TABULADOR_ERROR_TEXT)) {
            setReportStatusMessage('Tabulador capturado. Ya puedes generar el papel de trabajo.');
        }
    }
}

function setTabuladorError(message) {
    const errorEl = document.getElementById('tabulador-error');
    if (!errorEl) {
        return;
    }
    if (message) {
        errorEl.style.display = 'block';
        errorEl.textContent = message;
    } else {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }
}

function markTabuladorDirty() {
    if (tabuladorState.isLoading) {
        return;
    }
    tabuladorState.isDirty = true;
    updateTabuladorSaveStatus('Tienes cambios sin guardar en el tabulador ISR.', 'warning');
}

function setTabuladorSavedState(updatedAt) {
    tabuladorState.isDirty = false;
    tabuladorState.hasSavedSnapshot = true;
    tabuladorState.lastSavedAt = updatedAt || new Date().toISOString();
    const formatted = formatTimestamp(tabuladorState.lastSavedAt);
    updateTabuladorSaveStatus(formatted ? `Última actualización: ${formatted}` : 'Tabulador guardado correctamente.', 'success');
}

function updateTabuladorSaveStatus(message, tone = 'info') {
    const statusElement = document.getElementById('tabulador-save-status');
    if (!statusElement) {
        return;
    }
    statusElement.textContent = message || '';
    statusElement.classList.remove('status-info', 'status-success', 'status-error', 'status-warning');
    if (message) {
        statusElement.classList.add(`status-${tone}`);
    }
}

function formatTimestamp(timestamp) {
    if (!timestamp) {
        return '';
    }
    const parsedDate = new Date(timestamp);
    if (Number.isNaN(parsedDate.getTime())) {
        return '';
    }
    return parsedDate.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
}

async function loadSavedTabuladorData({ force = false, period = null } = {}) {
    if (tabuladorState.isDirty && !force) {
        return;
    }

    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }

    const requestedPeriod = typeof period === 'string' && period !== ''
        ? normalizePeriodString(period)
        : getTabuladorPeriod();
    const params = new URLSearchParams();
    if (requestedPeriod) {
        params.append('period', requestedPeriod);
    }
    const url = params.toString() ? `${TABULADOR_ENDPOINTS.check}?${params.toString()}` : TABULADOR_ENDPOINTS.check;

    tabuladorState.isLoading = true;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('HTTP ' + response.status);
        }
        const data = await response.json();
        if (data.period) {
            setActiveTabuladorPeriod(data.period);
        } else if (requestedPeriod) {
            setActiveTabuladorPeriod(requestedPeriod);
        }

        if (data.has_data && Array.isArray(data.rows) && data.rows.length) {
            resetTabuladorTable(data.rows);
            applyTabuladorInputTooltips();
            setTabuladorSavedState(data.updated_at);
            setTabuladorError('');
            clearEmptyTabuladorErrorIfRecovered();
        } else {
            resetTabuladorTable();
            applyTabuladorInputTooltips();
            tabuladorState.isDirty = false;
            tabuladorState.hasSavedSnapshot = false;
            tabuladorState.lastSavedAt = null;
            const activePeriod = tabuladorState.currentPeriod || requestedPeriod;
            const message = activePeriod
                ? `No existe un tabulador guardado para el ejercicio ${activePeriod}.`
                : 'Aún no guardas un tabulador ISR.';
            updateTabuladorSaveStatus(message, 'info');
        }
    } catch (error) {
        console.error('Error loading tabulador:', error);
        updateTabuladorSaveStatus('No se pudo cargar el tabulador guardado.', 'error');
    } finally {
        tabuladorState.isLoading = false;
        updateGenerateButtonAvailability();
    }
}

async function handleTabuladorSave() {
    const rows = collectTabuladorData();
    if (!rows.length) {
        setTabuladorError('Debes capturar al menos una fila completa del tabulador ISR.');
        updateTabuladorSaveStatus('Captura el tabulador antes de guardarlo.', 'error');
        updateGenerateButtonAvailability();
        return;
    }

    const targetPeriod = getTabuladorPeriod();
    if (!targetPeriod) {
        updateTabuladorSaveStatus('Selecciona el ejercicio a procesar antes de guardar el tabulador ISR.', 'error');
        updateGenerateButtonAvailability();
        return;
    }

    const saved = await saveTabuladorDataToBackend(rows, { period: targetPeriod });
    if (saved) {
        setTabuladorError('');
    }
}

async function saveTabuladorDataToBackend(rows, { silent = false, period } = {}) {
    if (!rows.length) {
        return false;
    }

    const targetPeriod = normalizePeriodString(period ?? getTabuladorPeriod());
    if (!targetPeriod) {
        if (!silent) {
            updateTabuladorSaveStatus('Selecciona el ejercicio a procesar antes de guardar el tabulador ISR.', 'error');
        }
        return false;
    }

    const formData = new FormData();
    formData.append('periodo', targetPeriod);
    formData.append('tabulador_isr', JSON.stringify(rows));

    try {
        const response = await fetch(TABULADOR_ENDPOINTS.save, {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'No se pudo guardar el tabulador ISR.');
        }
        setActiveTabuladorPeriod(targetPeriod);
        setTabuladorSavedState(data.updated_at);
        return true;
    } catch (error) {
        console.error('Error saving tabulador:', error);
        if (!silent) {
            updateTabuladorSaveStatus(error instanceof Error ? error.message : 'No se pudo guardar el tabulador ISR.', 'error');
        }
        return false;
    }
}

async function persistTabuladorBeforeGenerating(rows, period) {
    if (!rows.length) {
        return false;
    }
    const targetPeriod = normalizePeriodString(period);
    if (!targetPeriod) {
        updateTabuladorSaveStatus('Selecciona el ejercicio a procesar para el tabulador ISR.', 'error');
        return false;
    }
    if (!tabuladorState.isDirty && tabuladorState.hasSavedSnapshot && tabuladorState.currentPeriod === targetPeriod) {
        return true;
    }
    return saveTabuladorDataToBackend(rows, { silent: true, period: targetPeriod });
}

function updateGenerateButtonAvailability() {
    const generateBtn = document.getElementById('btn-generar-reporte');
    if (!generateBtn || generateBtn.dataset.generating === '1') {
        return;
    }

    const validation = validateReportGenerationInputs();
    generateBtn.disabled = false;
    generateBtn.title = validation.valid ? '' : validation.errors[0];
}

function handleTabuladorPaste(event) {
    const target = event.target;
    if (!target.classList.contains('tabulador-input')) {
        return;
    }

    const clipboardData = event.clipboardData?.getData('text');
    if (!clipboardData || (!clipboardData.includes('\t') && !clipboardData.includes('\n'))) {
        return;
    }

    event.preventDefault();
    const rows = clipboardData
        .split(/\r?\n/)
        .map(row => row.split('\t'))
        .filter(columns => columns.some(value => value.trim() !== ''));

    if (!rows.length) {
        return;
    }

    const tbody = getTabuladorTableBody();
    if (!tbody) {
        return;
    }

    const currentRow = target.closest('tr');
    const baseRowIndex = Array.from(tbody.children).indexOf(currentRow);
    const baseColIndex = Number(target.dataset.colIndex || 0);

    ensureTabuladorRowCount(baseRowIndex + rows.length);

    rows.forEach((rowValues, rowOffset) => {
        const rowElement = tbody.children[baseRowIndex + rowOffset];
        rowValues.forEach((cellValue, cellOffset) => {
            const columnIndex = baseColIndex + cellOffset;
            if (columnIndex >= TABULADOR_COLUMNS.length) {
                return;
            }
            const input = rowElement.querySelector(`.tabulador-input[data-col-index="${columnIndex}"]`);
            if (input) {
                input.value = cellValue.trim();
            }
        });
    });

    markTabuladorDirty();
    clearEmptyTabuladorErrorIfRecovered();
    updateGenerateButtonAvailability();
}

async function generarReporte() {
    const generateBtn = document.getElementById('btn-generar-reporte');
    if (!generateBtn) {
        return;
    }

    if (tabuladorState.isLoading) {
        setReportStatusMessage('Espera a que termine la carga del tabulador ISR antes de generar.', 'error');
        return;
    }

    const validation = validateReportGenerationInputs();
    if (!validation.valid) {
        const joinedMessage = validation.errors.join(' ');
        setTabuladorError(joinedMessage);
        setReportStatusMessage(joinedMessage, 'error');
        updateTabuladorSaveStatus(joinedMessage, 'error');
        updateGenerateButtonAvailability();
        return;
    }

    const tabuladorData = collectTabuladorData();
    setTabuladorError('');

    const tabuladorPeriod = validation.tabuladorPeriod;

    const persisted = await persistTabuladorBeforeGenerating(tabuladorData, tabuladorPeriod);
    if (!persisted) {
        setReportStatusMessage('No se pudo guardar el tabulador ISR. Revisa los datos e inténtalo nuevamente.', 'error');
        return;
    }

    const originalText = generateBtn.innerHTML;
    generateBtn.disabled = true;
    generateBtn.dataset.generating = '1';
    generateBtn.innerHTML = '⏳ Generando...';
    setReportStatusMessage('Procesando archivos para tu papel de trabajo, esto puede tardar unos segundos...');

    const reportPeriodSelect = document.getElementById('report-periodo');
    const selectedPeriod = reportPeriodSelect ? reportPeriodSelect.value : '';
    const formData = new FormData();
    if (selectedPeriod) {
        formData.append('periodo', selectedPeriod);
    }
    formData.append('tabulador_isr', JSON.stringify(tabuladorData));
    formData.append('tabulador_periodo', tabuladorPeriod);

    try {
        const response = await fetch('/api/reports/generate', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'No se pudo generar el papel de trabajo.');
        }

        if (data.success) {
            const periodo = data.periodo ? ` (Ejercicio ${data.periodo})` : '';
            setReportStatusMessage(`Papel de trabajo generado correctamente${periodo}.`, 'success');
            const viewerUrl = data.viewer_url || data.report_url || PAPERWORKS_VIEWER_DEFAULT_URL;
            setReportLinkState(true, viewerUrl, document.getElementById('modal-report-download'), document.getElementById('ver-reporte-btn'));
            refreshReportStatus();
        } else {
            const message = data.message || 'No se pudo generar el papel de trabajo.';
            setReportStatusMessage(message, 'error');
        }
    } catch (error) {
        console.error('Error generating report:', error);
        const message = error instanceof Error ? error.message : 'Error inesperado al generar el papel de trabajo.';
        setReportStatusMessage(message, 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = originalText;
        delete generateBtn.dataset.generating;
        updateGenerateButtonAvailability();
    }
}

// Cargar datos del contribuyente en el formulario
function loadContribuyenteData(data) {
    const modalObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            const modal = document.getElementById('contribuyente-modal');
            if (modal && modal.classList.contains('active') && data.has_data) {
                document.getElementById('nombre').value = data.nombre || '';
                document.getElementById('rfc').value = data.rfc || '';
                document.getElementById('curp').value = data.curp || '';
            }
        });
    });
    
    const modal = document.getElementById('contribuyente-modal');
    if (modal) {
        modalObserver.observe(modal, { attributes: true, attributeFilter: ['class'] });
    }
}

function setReportPeriodValue(periodo) {
    const normalized = normalizePeriodString(periodo);
    if (!normalized) {
        return;
    }
    const selector = document.getElementById('report-periodo');
    if (!selector) {
        return;
    }
    const hasOption = Array.from(selector.options).some(option => option.value === normalized);
    if (!hasOption) {
        const option = document.createElement('option');
        option.value = normalized;
        option.textContent = `Ejercicio ${normalized}`;
        selector.appendChild(option);
    }
    selector.value = normalized;
}

// Limpiar formulario del contribuyente
function clearContribuyenteForm() {
    document.getElementById('nombre').value = '';
    document.getElementById('rfc').value = '';
    document.getElementById('curp').value = '';
}

// Validar RFC en tiempo real
function validateRfcInput() {
    const rfcInput = document.getElementById('rfc');
    const rfc = rfcInput.value.toUpperCase();
    rfcInput.value = rfc;
    
    if (rfc.length === 0) return;
    
    const rfcPattern = /^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/;
    if (rfc.length === 13 && !rfcPattern.test(rfc)) {
        rfcInput.style.borderColor = 'var(--danger-color)';
    } else {
        rfcInput.style.borderColor = 'var(--border-color)';
    }
}

// Validar CURP en tiempo real
function validateCurpInput() {
    const curpInput = document.getElementById('curp');
    const curp = curpInput.value.toUpperCase();
    curpInput.value = curp;
    
    if (curp.length === 0) return;
    
    const curpPattern = /^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$/;
    if (curp.length === 18 && !curpPattern.test(curp)) {
        curpInput.style.borderColor = 'var(--danger-color)';
    } else {
        curpInput.style.borderColor = 'var(--border-color)';
    }
}

// Guardar datos del contribuyente
async function saveContribuyente(event) {
    event.preventDefault();
    
    const formData = new FormData();
    formData.append('nombre', document.getElementById('nombre').value);
    formData.append('rfc', document.getElementById('rfc').value);
    formData.append('curp', document.getElementById('curp').value);
    // Mostrar spinner
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<div class="spinner"></div> Guardando...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/contribuyente', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`✅ ${result.message}\n\nRFC: ${result.data.rfc}`, 'success');
            
            // Cerrar modal y recargar después de 2 segundos
            setTimeout(() => {
                closeModal('contribuyente-modal');
                location.reload();
            }, 2000);
        } else {
            showAlert(`❌ Error: ${result.message}`, 'error');
        }
    } catch (error) {
        showAlert(`❌ Error de conexión: ${error.message}`, 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Función de ayuda
function showHelp() {
    alert(`📖 AYUDA DEL SISTEMA

1. CONFIGURAR FIEL
   - Configura tus certificados .cer y .key del SAT
   - Necesarios para descargar documentos

2. DESCARGAR DEL SAT
   - Descarga automática de CFDIs y retenciones
   - Requiere configuración FIEL previa

3. DATOS DEL CONTRIBUYENTE
    - Captura tus datos fiscales (RFC, CURP, etc.)
    - Necesario para generar papeles de trabajo

4. PROCESAR Y GENERAR
    - Procesa los documentos descargados
    - Genera papel de trabajo en Excel

📧 Para más información, consulta la documentación`);
}

// Cargar información de FIEL en el modal de descarga
function loadFielInfo() {
    fetch('/api/fiel/status')
        .then(response => response.json())
        .then(data => {
            if (data.has_config) {
                document.getElementById('fiel-info-box').style.display = 'block';
                document.getElementById('fiel-rfc-display').textContent = `RFC: ${data.rfc}`;
                document.getElementById('fiel-nombre-display').textContent = `Nombre: ${data.nombre}`;
            } else {
                showAlert('⚠️ No has configurado tu FIEL. Por favor configúrala primero.', 'warning');
                closeModal('download-modal');
                setTimeout(() => openModal('fiel-modal'), 500);
            }
        })
        .catch(error => {
            console.error('Error loading FIEL info:', error);
            showAlert('Error al verificar la configuración FIEL', 'error');
        });
}

// Actualizar campos de fecha según el tipo de descarga
function updateDateFields() {
    const tipoDescarga = document.querySelector('input[name="tipo_descarga"]:checked').value;
    
    const anioField = document.getElementById('anio-field');
    const mesField = document.getElementById('mes-field');
    const rangoFields = document.getElementById('rango-fields');
    
    // Ocultar todos primero
    anioField.style.display = 'none';
    mesField.style.display = 'none';
    rangoFields.style.display = 'none';
    
    // Mostrar según la opción
    if (tipoDescarga === 'anio_completo') {
        anioField.style.display = 'block';
    } else if (tipoDescarga === 'mes_especifico') {
        anioField.style.display = 'block';
        mesField.style.display = 'block';
    } else if (tipoDescarga === 'rango_personalizado') {
        rangoFields.style.display = 'block';
    }
}

// Iniciar descarga
async function iniciarDescarga(event) {
    event.preventDefault();
    
    // Validaciones previas
    const tipoDescarga = document.querySelector('input[name="tipo_descarga"]:checked').value;
    const docNomina = document.querySelector('input[name="doc_nomina"]').checked;
    const docRetenciones = document.querySelector('input[name="doc_retenciones"]').checked;
    const docIngresos = document.querySelector('input[name="doc_ingresos"]').checked;
    const password = document.getElementById('fiel_password_download').value;
    
    // Validar que al menos un tipo de documento esté seleccionado
    if (!docNomina && !docRetenciones && !docIngresos) {
        showAlert('Debes seleccionar al menos un tipo de documento', 'warning');
        return;
    }
    
    // Validar contraseña
    if (!password) {
        showAlert('Debes ingresar la contraseña de la FIEL', 'warning');
        return;
    }
    
    // Validar fechas para rango personalizado
    if (tipoDescarga === 'rango_personalizado') {
        const fechaInicio = document.getElementById('fecha_inicio').value;
        const fechaFin = document.getElementById('fecha_fin').value;
        
        if (!fechaInicio || !fechaFin) {
            showAlert('Debes ingresar fecha de inicio y fin', 'warning');
            return;
        }
        if (new Date(fechaFin) < new Date(fechaInicio)) {
            showAlert('La fecha fin debe ser mayor o igual a la fecha inicio', 'warning');
            return;
        }

        const inicioDate = new Date(fechaInicio);
        const finDate = new Date(fechaFin);
        const maxFinPermitida = addOneCalendarYear(inicioDate);
        if (finDate > maxFinPermitida) {
            showAlert('El rango personalizado no puede ser mayor a 1 año calendario.', 'warning');
            return;
        }
    }
    
    // Cerrar modal de descarga
    closeModal('download-modal');
    
    // Limpiar campo de contraseña por seguridad
    document.getElementById('fiel_password_download').value = '';
    
    // Esperar a que se cierre el modal y ejecutar descarga
    setTimeout(() => ejecutarDescarga(password), 400);
}

// Ejecutar la descarga real con Server-Sent Events
function ejecutarDescarga(password) {
    // Mostrar popup de progreso
    const progressPopup = document.getElementById('progress-popup');
    progressPopup.classList.add('active');
    progressPopup.style.display = 'flex';
    
    const tipoDescarga = document.querySelector('input[name="tipo_descarga"]:checked').value;
    const anio = document.getElementById('anio_fiscal').value;
    const mes = document.getElementById('mes').value;
    const fechaInicio = document.getElementById('fecha_inicio').value;
    const fechaFin = document.getElementById('fecha_fin').value;
    
    const docNomina = document.querySelector('input[name="doc_nomina"]').checked;
    const docRetenciones = document.querySelector('input[name="doc_retenciones"]').checked;
    const docIngresos = document.querySelector('input[name="doc_ingresos"]').checked;
    const documentStatus = document.querySelector('input[name="document_status"]:checked').value;
    const filterFechaPago = document.querySelector('input[name="filter_fecha_pago"]').checked;
    const verDescargasBtn = document.getElementById('ver-descargas-btn');
    
    const progressText = document.getElementById('progress-text');
    const progressFill = document.getElementById('progress-fill');
    const progressLog = document.getElementById('progress-log');
    const progressFooter = document.getElementById('progress-footer');
    const requestCounter = document.getElementById('request-counter');
    
    function hideProgressPopup() {
        progressPopup.classList.remove('active');
        progressPopup.style.display = 'none';
    }

    function showCloseFooter() {
        progressFooter.innerHTML = '';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn btn-secondary';
        closeBtn.textContent = 'Cerrar';
        closeBtn.addEventListener('click', hideProgressPopup);
        progressFooter.appendChild(closeBtn);
        progressFooter.style.display = 'block';
    }

    progressText.innerHTML = '<p>⏳ Preparando procesos de descarga...</p>';
    progressFill.style.width = '0%';
    progressFill.textContent = '0%';
    progressFill.classList.add('animating');
    progressLog.innerHTML = '<p class="info">🔄 Preparando conexión...</p>';
    progressFooter.style.display = 'none';
    requestCounter.style.display = 'none';

    const sharedPayload = {
        tipo_descarga: tipoDescarga,
        anio,
        mes,
        fecha_inicio: fechaInicio,
        fecha_fin: fechaFin,
        document_status: documentStatus,
        fiel_password: password,
        filter_fecha_pago: filterFechaPago ? '1' : '0'
    };

    const tasks = buildDownloadTasks();
    const totalStages = tasks.length;
    const stageSummaries = [];
    let globalProgress = 0;

    function setProgressBar(percent) {
        const safePercent = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
        progressFill.style.width = safePercent + '%';
        progressFill.textContent = safePercent + '%';
    }

    function updateGlobalProgress(stageIndex, stagePercent, allowDecrease = false) {
        if (!totalStages) {
            return;
        }

        const safeStageIndex = Math.max(0, Math.min(totalStages - 1, Number(stageIndex) || 0));
        const safeStagePercent = Math.max(0, Math.min(100, Number(stagePercent) || 0));
        const stageSize = 100 / totalStages;
        const mappedPercent = (safeStageIndex * stageSize) + (safeStagePercent / 100) * stageSize;
        const nextPercent = allowDecrease ? mappedPercent : Math.max(globalProgress, mappedPercent);

        globalProgress = Math.max(0, Math.min(100, nextPercent));
        setProgressBar(globalProgress);
    }

    function formatStageProgressMessage(stage, message) {
        const rawMessage = String(message || '');
        if (!stage) {
            return rawMessage;
        }

        if (/^(Nomina|Retenciones|Ingresos)\s+/i.test(rawMessage)) {
            return rawMessage.replace(/^(Nomina|Retenciones|Ingresos)\s+/i, 'Peticiones ');
        }

        return rawMessage;
    }

    if (!totalStages) {
        progressFill.classList.remove('animating');
        progressText.innerHTML = '<p class="error">❌ No se detectaron procesos a ejecutar</p>';
        appendLog('No se detectaron tipos de documentos seleccionados.', 'error');
        showCloseFooter();
        return;
    }

    appendLog(`Se configuraron ${totalStages} proceso(s) de descarga.`, 'info');
    runStage(0);

    function buildDownloadTasks() {
        const stages = [];
        const needsCfdi = docNomina || docIngresos;

        if (needsCfdi) {
            const flags = {
                doc_nomina: docNomina ? '1' : '0',
                doc_ingresos: docIngresos ? '1' : '0',
                doc_retenciones: '0'
            };
            stages.push({
                label: docNomina && docIngresos ? 'Nómina + Otros CFDI' : (docNomina ? 'Nómina' : 'Otros CFDI'),
                params: buildParams(flags),
                expectedRequests: estimateRequests(flags)
            });
        }

        if (docRetenciones) {
            const flags = {
                doc_nomina: '0',
                doc_ingresos: '0',
                doc_retenciones: '1'
            };
            stages.push({
                label: 'Constancias de retenciones',
                params: buildParams(flags),
                expectedRequests: estimateRequests(flags)
            });
        }

        return stages;
    }

    function buildParams(flags) {
        const params = new URLSearchParams();
        Object.entries(sharedPayload).forEach(([key, value]) => {
            params.append(key, value ?? '');
        });
        params.append('doc_nomina', flags.doc_nomina);
        params.append('doc_retenciones', flags.doc_retenciones);
        params.append('doc_ingresos', flags.doc_ingresos);
        return params;
    }

    function estimateRequests(flags) {
        let count = 0;
        if (flags.doc_nomina === '1') count++;
        if (flags.doc_ingresos === '1') count++;
        if (flags.doc_retenciones === '1') count++;
        if (documentStatus === 'both') {
            count *= 2;
        }
        return count || 1;
    }

    function runStage(stageIndex) {
        if (stageIndex >= totalStages) {
            progressFill.classList.remove('animating');
            progressText.innerHTML = '<p class="success">✅ Todos los procesos completados</p>';
            requestCounter.innerHTML = '📊 Todos los procesos finalizaron correctamente';
            requestCounter.style.display = 'block';
            appendFinalSummaries();
            showCloseFooter();
            return;
        }

        const stage = tasks[stageIndex];
        updateGlobalProgress(stageIndex, 0);
        progressFill.classList.add('animating');
        progressText.innerHTML = `<p>🚀 ${stage.label} (${stageIndex + 1} de ${totalStages})</p>`;
        requestCounter.innerHTML = `📊 Proceso ${stageIndex + 1} de ${totalStages}: <strong>${stage.label}</strong> (${stage.expectedRequests} peticiones previstas)`;
        requestCounter.style.display = 'block';
        appendLog(`▶️ Iniciando ${stage.label}...`, 'info');
        progressFooter.style.display = 'none';

        startSSE(stage, stageIndex)
            .then(() => runStage(stageIndex + 1))
            .catch(() => {
                // El error ya se mostró en pantalla
            });
    }

    function startSSE(stage, stageIndex) {
        return new Promise((resolve, reject) => {
            fetch('/api/sat/download/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: stage.params.toString()
            }).then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let finished = false;

                function closeStream() {
                    if (finished) {
                        return;
                    }
                    finished = true;
                    reader.cancel().catch(() => {});
                }

                function processText(text) {
                    if (finished) {
                        return;
                    }
                    buffer += text;
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop();

                    lines.forEach(line => {
                        if (!line.trim()) {
                            return;
                        }
                        const eventMatch = line.match(/^event: ([\w-]+)\ndata: (.+)$/);
                        if (!eventMatch) {
                            return;
                        }
                        const eventType = eventMatch[1];
                        const data = JSON.parse(eventMatch[2]);
                        handleSSEEvent(eventType, data);
                    });
                }

                function pump() {
                    return reader.read().then(({ done, value }) => {
                        if (done || finished) {
                            return;
                        }
                        processText(decoder.decode(value, { stream: true }));
                        return pump();
                    });
                }

                pump();

                function handleSSEEvent(eventType, data) {
                    if (eventType === 'progress') {
                        const formattedMessage = formatStageProgressMessage(stage, data.message);
                        updateGlobalProgress(stageIndex, data.percent);
                        progressText.innerHTML = `<p>${stage.label}: ${formattedMessage}</p>`;
                        appendLog(`${stage.label}: ${formattedMessage}`, 'info');
                    } else if (eventType === 'retry') {
                        const retryMsg = `🔄 ${stage.label} - Reintento ${data.attempt} de ${data.max}: ${data.message}`;
                        progressText.innerHTML = `<p class="warning">${retryMsg}</p>`;
                        appendLog(retryMsg, 'warning');
                    } else if (eventType === 'success') {
                        progressFill.classList.remove('animating');
                        updateGlobalProgress(stageIndex, 100);
                        const headerMsg = `✅ ${stage.label} completado`;
                        progressText.innerHTML = `<p class="success">${headerMsg}</p>`;
                        appendLog(headerMsg, 'success');
                        appendLog('═══════════════════════════════════', 'info');

                        const result = data || {};
                        const summary = result.summary || {};
                        const totalArchivos = Number(result.total_archivos || 0);
                        const totalReintentos = Number(result.total_reintentos || 0);
                        const peticionesRealizadas = result.peticiones_realizadas ?? stage.expectedRequests;
                        const includeNomina = stage.params.get('doc_nomina') === '1';
                        const includeRetenciones = stage.params.get('doc_retenciones') === '1';
                        const includeIngresos = stage.params.get('doc_ingresos') === '1';

                        stageSummaries.push({
                            label: stage.label,
                            totalArchivos,
                            totalReintentos,
                            peticionesRealizadas,
                            expectedRequests: stage.expectedRequests,
                            includeNomina,
                            includeRetenciones,
                            includeIngresos,
                            summary,
                            periodo: result.periodo,
                            fechaPagoFilter: result.fecha_pago_filter || {},
                        });

                        if (totalArchivos === 0) {
                            progressText.innerHTML = `<p class="info">⚠️ ${stage.label} completado - Sin documentos</p>`;
                        }

                        if (verDescargasBtn) {
                            const link = DOWNLOADS_VIEWER_DEFAULT_URL;
                            if (totalArchivos > 0) {
                                setVerDescargasButtonState(true, link, verDescargasBtn);
                            } else {
                                verDescargasBtn.href = link;
                            }
                            refreshVerDescargasButtonState();
                        }

                        if (stageIndex === totalStages - 1) {
                            appendLog('🏁 Procesos finalizados. Generando resumen final...', 'info');
                        } else {
                            appendLog('➡️ Continuando con el siguiente proceso...', 'info');
                        }

                        closeStream();
                        resolve(result);
                    } else if (eventType === 'error') {
                        progressFill.classList.remove('animating');
                        const errorMsg = data.message || `❌ Error en ${stage.label}`;
                        progressText.innerHTML = `<p class="error">${errorMsg}</p>`;
                        appendLog(errorMsg, 'error');
                        showCloseFooter();
                        closeStream();
                        reject(new Error(errorMsg));
                    }
                }
            }).catch(error => {
                progressFill.classList.remove('animating');
                const message = `❌ Error de conexión en ${stage.label}: ${error.message}`;
                progressText.innerHTML = `<p class="error">${message}</p>`;
                appendLog(message, 'error');
                showCloseFooter();
                reject(error);
            });
        });
    }

    function appendFinalSummaries() {
        if (!stageSummaries.length) {
            return;
        }

        appendLog('═══════════════════════════════════', 'info');
        appendLog('📋 Resumen final por tipo de XML', 'success');

        stageSummaries.forEach((stageSummary, index) => {
            appendLog('═══════════════════════════════════', 'info');
            appendLog(`✅ Resumen ${stageSummary.label}`, 'success');
            appendLog(`📦 Archivos descargados: ${stageSummary.totalArchivos}`, 'success');
            appendLog(`♻️ Reintentos usados: ${stageSummary.totalReintentos}`, 'success');

            if (stageSummary.includeNomina && stageSummary.summary.nominas !== undefined) {
                appendLog(`· Nóminas: ${stageSummary.summary.nominas}`, 'success');
            }
            if (stageSummary.includeRetenciones && stageSummary.summary.retenciones !== undefined) {
                appendLog(`· Retenciones: ${stageSummary.summary.retenciones}`, 'success');
            }
            if (stageSummary.includeIngresos && stageSummary.summary.ingresos !== undefined) {
                appendLog(`· Otros CFDI: ${stageSummary.summary.ingresos}`, 'success');
            }

            if (stageSummary.fechaPagoFilter.removed > 0) {
                appendLog(`🧹 XML descartados por FechaPago: ${stageSummary.fechaPagoFilter.removed}`, 'success');
            }

            if (stageSummary.periodo) {
                appendLog(`📅 Periodo: ${stageSummary.periodo}`, 'success');
            }

            appendLog(
                `📊 Peticiones realizadas: ${stageSummary.peticionesRealizadas} de ${stageSummary.expectedRequests}`,
                'info'
            );

            if (index === stageSummaries.length - 1) {
                appendLog('═══════════════════════════════════', 'info');
            }
        });
    }

    function appendLog(text, tone = 'info') {
        const entry = document.createElement('p');
        entry.className = tone;
        entry.textContent = text;
        progressLog.appendChild(entry);
        progressLog.scrollTop = progressLog.scrollHeight;
    }
}

