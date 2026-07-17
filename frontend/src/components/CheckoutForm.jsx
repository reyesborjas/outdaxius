// frontend/src/components/CheckoutForm.jsx
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY);

function CheckoutForm({ bookingId, amount }) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!stripe || !elements) return;
    
    setProcessing(true);
    setError(null);

    const { error: submitError } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/booking/${bookingId}/success`,
      },
    });

    if (submitError) {
      setError(submitError.message);
      setProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      
      <button 
        type="submit" 
        disabled={!stripe || processing}
        className="btn btn-primary w-100 mt-3"
      >
        {processing ? 'Procesando...' : `Pagar $${amount.toLocaleString('es-CL')}`}
      </button>
      
      {error && <div className="alert alert-danger mt-2">{error}</div>}
      
      <div className="text-muted small mt-2 text-center">
        El pago va directamente a la agencia de viajes.<br/>
        Procesado de forma segura por Stripe.
      </div>
    </form>
  );
}

export default function BookingCheckout({ booking }) {
  const [clientSecret, setClientSecret] = useState(null);
  const { token } = useAuth();

  useEffect(() => {
    fetch(`${API}/payments/stripe/bookings/${booking.id}/create-payment-intent`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setClientSecret(data.client_secret));
  }, [booking.id, token]);

  if (!clientSecret) return <div>Cargando...</div>;

  return (
    <Elements stripe={stripePromise} options={{ clientSecret }}>
      <CheckoutForm bookingId={booking.id} amount={booking.amount} />
    </Elements>
  );
}
