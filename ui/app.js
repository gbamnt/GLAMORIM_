// Ponte com o Python: window.pywebview.api.* (sem HTTP).
function api() {
  return window.pywebview && window.pywebview.api;
}

document.addEventListener('alpine:init', () => {
  Alpine.data('shell', () => ({
    tela: 'painel',
    versao: '',
    ponte: false,
    nav: [
      { id: 'painel', label: 'Painel' },
      { id: 'produtos', label: 'Produtos' },
      { id: 'contas', label: 'Contas' },
      { id: 'cartoes', label: 'Cartões' },
      { id: 'historico', label: 'Histórico' },
      { id: 'config', label: 'Configurações' },
    ],
    async init() {
      const ready = async () => {
        this.ponte = true;
        const info = await api().app_info();
        this.versao = info.versao;
      };
      if (api()) await ready();
      else window.addEventListener('pywebviewready', ready, { once: true });
    },
    lock() { /* etapa A2 */ },
  }));
});
