import streamlit as st
from services import cart, checkout
from services.products import money
from services.ui import token, summary, error_message


def render():
    st.title('Finalize sua compra')
    st.write('Confira os itens. Esta é uma demonstração acadêmica, sem cobrança.')
    try:
        auth = token()
        customer = cart.authenticate(auth)
        if st.session_state.get('last_order'):
            st.success(f"Compra confirmada! Pedido {st.session_state.last_order}.")
        current = cart.read_cart(auth)
        if current['items']:
            lines = current['order']['itens'] if current['pending'] else cart.cart_lines(current)
            summary(lines)
            if current['pending']:
                st.warning('Compra interrompida. O resumo foi preservado para retomada.')
            if st.button('Retomar compra' if current['pending'] else 'Confirmar compra', type='primary'):
                # O ID permanece no carrinho até a conclusão, inclusive após recarregar a tela.
                with st.spinner('Registrando seu pedido…'):
                    saved = checkout.complete(auth)
                st.session_state.last_order = saved['_id']
                st.rerun()
        else:
            st.info('Adicione produtos ao carrinho para fazer uma nova compra.')
        st.subheader('Seus pedidos e compras pendentes')
        saved_orders = checkout.orders(auth)
        known = {x['_id'] for x in saved_orders}
        drafts = cart.pending_drafts(customer['cliente_id'])
        pending = [dict(x, status='aguardando_gravacao') for x in drafts if x['_id'] not in known]
        for order in pending + saved_orders:
            with st.expander(f"Pedido {order['_id'][:12]} · {money(order['total_centavos'])} · {order['status']}"):
                summary(order['itens'])
                if order['status'] != 'concluido':
                    if st.button('Retomar este pedido', key=f"resume_{order['_id']}"):
                        result = checkout.complete(auth, order['_id'])
                        st.session_state.last_order = result['_id']
                        st.rerun()
        if not pending and not saved_orders:
            st.caption('Você ainda não tem pedidos registrados.')
    except Exception as error:
        error_message(error)
        st.info('Se você já confirmou uma compra, tente novamente ou retome o pedido abaixo após restabelecer as conexões. O mesmo identificador será reutilizado.')
