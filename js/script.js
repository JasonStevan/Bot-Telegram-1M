function toggleBotStatus() {
    // Desabilitar o botão enquanto a requisição é processada
    const toggleBtn = document.getElementById('toggleBotBtn');
    if (toggleBtn) {
        toggleBtn.disabled = true;
        toggleBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Aguarde...';
    }
    
    // Enviar requisição para alternar status
    fetch('/toggle_bot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Atualizar interface
            if (toggleBtn) {
                toggleBtn.disabled = false;
                toggleBtn.innerHTML = data.active ? 'Desativar Bot' : 'Ativar Bot';
                toggleBtn.className = data.active ? 'btn btn-danger' : 'btn btn-success';
            }
            
            // Mostrar mensagem de sucesso
            showAlert(data.message, 'success');
            
            // Recarregar a página após 1 segundo para refletir a mudança
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            // Mostrar erro e restaurar botão
            showAlert('Erro: ' + data.message, 'danger');
            if (toggleBtn) {
                toggleBtn.disabled = false;
                toggleBtn.innerHTML = 'Alternar Status';
            }
        }
    })
    .catch(error => {
        // Tratar erro de rede
        showAlert('Erro de comunicação: ' + error.message, 'danger');
        if (toggleBtn) {
            toggleBtn.disabled = false;
            toggleBtn.innerHTML = 'Alternar Status';
        }
    });
}

function showAlert(message, type) {
    // Criar elemento de alerta
    const alertContainer = document.getElementById('alertContainer') || document.createElement('div');
    if (!document.getElementById('alertContainer')) {
        alertContainer.id = 'alertContainer';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }
    
    // Criar alerta
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Adicionar alerta ao container
    alertContainer.appendChild(alert);
    
    // Remover alerta após 5 segundos
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alertContainer.removeChild(alert);
        }, 150);
    }, 5000);
}
