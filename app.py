import streamlit as st
from services import cart
from services.products import customers
from services.health import check_connections
from services.ui import error_message

st.set_page_config(page_title='E-Commerce Inteligente', page_icon='🛍️', layout='wide')
with st.sidebar:
    st.title('E-Commerce Inteligente')
    st.caption('Tecnologia para o seu dia.')
    st.divider()
    st.subheader('Cliente de demonstração')
    st.caption('Identificação simples, sem senha ou pagamento real.')
    try:
        if st.session_state.get('token'):
            try:
                session = cart.authenticate(st.session_state.token)
                st.success(f"Olá, {session['nome'].split()[0]}!")
                if st.button('Encerrar sessão'):
                    cart.logout(st.session_state.token)
                    st.session_state.pop('token', None)
                    st.session_state.pop('last_order', None)
                    st.rerun()
            except ValueError:
                st.session_state.pop('token', None)
                st.warning('Sua sessão expirou. Identifique-se novamente.')
        if not st.session_state.get('token'):
            choices = customers()
            if choices:
                chosen = st.selectbox('Escolha um cliente', choices, format_func=lambda x: x['nome'])
                if st.button('Iniciar sessão', type='primary'):
                    st.session_state.token = cart.login(chosen)
                    st.rerun()
            else:
                st.info('Inicialize os dados para selecionar um cliente.')
    except Exception as error:
        error_message(error)
    with st.expander('Diagnóstico dos bancos'):
        if st.button('Verificar conexões'):
            with st.spinner('Verificando…'):
                results = check_connections()
            for result in results:
                (st.success if result['ok'] else st.error)(f"{result['banco']}: {result['detalhe']}")
    st.caption('Projeto acadêmico · Python + NoSQL')

from pages import catalog, cart_page, recommendations_page, checkout_page

screens = {
    'Catálogo': catalog.render,
    'Carrinho': cart_page.render,
    'Recomendações': recommendations_page.render,
    'Checkout': checkout_page.render,
}
selected = st.sidebar.radio('Navegação', list(screens), key='page')
screens[selected]()
