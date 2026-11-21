import streamlit as st
from services import cart
from services.products import money
from services.ui import token, summary, error_message

from services.ui import navigate

def render():
    st.title('Seu carrinho')
    st.write('Ajuste as quantidades antes de finalizar a compra.')
    try:
        auth = token()
        current = cart.read_cart(auth)
        if current['pending']:
            st.warning('Uma compra deste carrinho está em processamento. Retome pelo Checkout.')
            summary(current['order']['itens'])
            navigate('Retomar checkout', 'Checkout')
        elif not current['items']:
            st.info('Seu carrinho está vazio.')
            navigate('Explorar catálogo', 'Catálogo')
        else:
            lines = cart.cart_lines(current)
            for line in lines:
                with st.container(border=True):
                    name, quantity, remove = st.columns([3, 2, 1])
                    name.markdown(f"**{line['nome']}**")
                    name.caption(f"{money(line['preco_centavos'])} por unidade")
                    with quantity.form(f"quantity_{current['id']}_{line['produto_id']}"):
                        value = st.number_input('Quantidade', min_value=1, max_value=99, value=line['quantidade'])
                        if st.form_submit_button('Atualizar'):
                            cart.change_cart(auth, line['produto_id'], value)
                            st.rerun()
                    if remove.button('Remover', key=f"remove_{line['produto_id']}"):
                        cart.change_cart(auth, line['produto_id'], 0)
                        st.rerun()
            st.metric('Total', money(sum(x['subtotal_centavos'] for x in lines)))
            if st.button('Esvaziar carrinho'):
                cart.change_cart(auth, clear=True)
                st.rerun()
            navigate('Continuar para checkout', 'Checkout')
    except Exception as error:
        error_message(error)
