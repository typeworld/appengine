let stripe;
let elements;
let element;
let elementName;
let config;

function setupStripeElement(incomingElementName) {

  fetch('/stripe-config', {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      paymentMethod: incomingElementName,
    }),
  })
  .then((response) => {
    return response.json();
  })
  .then((response) => {
    config = response;
    setupStripe(incomingElementName);
  })


  // return fetch('/stripe-config', {
  //   method: 'get',
  //   headers: {
  //     'Content-Type': 'application/json',
  //   },
  // })
  //   .then((response) => {
  //     return response.json();
  //   })
  //   .then((response) => {
  //     setupStripe(response, incomingElementName);
  //   })
}

function setupStripe(incomingElementName) {
  stripe = Stripe(config.publishableKey);
  elements = stripe.elements();
  elementName = incomingElementName;

  if (elementName == "card") {
    element = elements.create('card', {hidePostalCode: true});
    element.mount('#' + elementName + '-element');
    // Error handling
    element.on('change', function (event) {
      displayError(event);
    });
  }

  else if (elementName == "iban") {
    element = elements.create('iban', {
      supportedCountries: ['SEPA'],
      placeholderCountry: config.customerCountry,
    });
    element.mount('#' + elementName + '-element');
    // Error handling
    element.on('change', function (event) {
      displayError(event);
    });
  }

}


function displayError(event) {
  console.log("displayError()", event);

  let displayError = document.getElementById('card-element-errors');
  if (event.error) {
    console.log("Error:" + event.error.message);
    displayError.textContent = '▲ ' + event.error.message;
  } else {
    displayError.textContent = '';
  }
  enableButtons();
}


function createInitialSubscription(productId) {
  console.log("1 - createInitialSubscription()");
  processPaymentMethod(productId, '/create-subscription');
}

function updatePaymentMethod() {
  console.log("1 - updatePaymentMethod()");
  processPaymentMethod(null, '/update-payment-method');
}

function createAdditionalSubscription(productId) {
  console.log("3 - createAdditionalSubscription()");
  callServer({
    paymentMethodId: null,
    productId: productId,
    url: '/create-subscription',
  });
}




function processPaymentMethod(productId, url) {
  console.log("2 - processPaymentMethod()");


  if (elementName == "card") {
    return stripe
    .createPaymentMethod({
      type: 'card',
      card: element,
    })
    .then((result) => {
      if (result.error) {
        displayError(result.error);
      } else {
        callServer({
          paymentMethodId: result.paymentMethod.id,
          productId: productId,
          url: url,
        });
      }
    })
    .catch(displayError)
  }

  else if (elementName == "iban") {
    stripe
    .confirmSepaDebitSetup(config.clientSecret, {
      payment_method: {
        sepa_debit: element,
        billing_details: {
          name: $("#account-holder-name").val(),
          email: config.customerEmail,
        },
      },
    })
    .then(function(result) {
      if (result.error) {
        displayError(result.error);
      } else {
        callServer({
          paymentMethodId: result.setupIntent.payment_method,
          productId: productId,
          url: url,
        });
      }
    })
    .catch(displayError)
  }

}


function callServer({paymentMethodId, productId, url}) {
  console.log("3 - callServer()");
  return (
    fetch(url, {
      method: 'post',
      headers: {
        'Content-type': 'application/json',
      },
      body: JSON.stringify({
        paymentMethodId: paymentMethodId,
        productId: productId,
      }),
    })
    .then((response) => {
      return response.json();
    })
    // If the card is declined, display an error to the user.
    .then((result) => {
      if (result.error) {
        // The card had an error when trying to attach it to a customer.
        displayError(result.error);
      }
      return result;
    })
    // Normalize the result to contain the object returned by Stripe.
    // Add the additional details we need.
    .then((result) => {
      return {
        subscription: result,
        paymentMethodId: paymentMethodId,
        invoice: result.latest_invoice,
      };
    })
    // Some payment methods require a customer to do additional
    // authentication with their financial institution.
    // Eg: 2FA for cards.
    .then(handleCardSetupRequired)
    .then(handlePaymentThatRequiresCustomerAction)
    // If attaching this card to a Customer object succeeds,
    // but attempts to charge the customer fail. You will
    // get a requires_payment_method error.
    .then(handleRequiresPaymentMethod)
    // No more actions required. Provision your service for the user.
    .then(onSubscriptionComplete)
    .catch(displayError)
  );
}





function handleCardSetupRequired({
  subscription,
  invoice,
  priceId,
  paymentMethodId
})
{
  console.log("4 - handleCardSetupRequired()");
  // console.log("handleCardSetupRequired()", 
  // subscription,
  // invoice,
  // priceId,
  // paymentMethodId);

  let setupIntent = subscription.pending_setup_intent;

  if (subscription.error) {
    throw subscription;
  }


  if (setupIntent && setupIntent.status === 'requires_action')
  {
    return stripe
      .confirmCardSetup(setupIntent.client_secret, {
        payment_method: paymentMethodId,
      })
      .then((result) => {
        if (result.error) {
          // start code flow to handle updating the payment details
          // Display error message in your UI.
          // The card was declined (i.e. insufficient funds, card has expired, etc)
          throw result;
        } else {
          if (result.setupIntent.status === 'succeeded') {
            // There's a risk of the customer closing the window before callback
            // execution. To handle this case, set up a webhook endpoint and
            // listen to setup_intent.succeeded.
            return {
              subscription,
              invoice,
              priceId,
              paymentMethodId,
            };
          }
        }
      });
  }
  else {
    // No customer action needed
    console.log("No action needed");
    return {
      subscription,
      invoice,
      priceId,
      paymentMethodId,
};
  }
}

function handlePaymentThatRequiresCustomerAction({
  subscription,
  invoice,
  priceId,
  paymentMethodId,
  isRetry
}) {
  console.log("5 - handlePaymentThatRequiresCustomerAction()");
  // console.log("handlePaymentThatRequiresCustomerAction()", 
  // subscription,
  // invoice,
  // priceId,
  // paymentMethodId,
  // isRetry
  // );
  // If it's a first payment attempt, the payment intent is on the subscription latest invoice.
  // If it's a retry, the payment intent will be on the invoice itself.
  let paymentIntent = invoice
    ? invoice.payment_intent
    : subscription.latest_invoice.payment_intent;

  if (!paymentIntent) {
    console.log("return immediately");
    return { subscription, priceId, paymentMethodId };
  }

  if (
    paymentIntent.status === 'requires_action' ||
    (isRetry === true && paymentIntent.status === 'requires_payment_method')
  ) {
    return stripe
      .confirmCardPayment(paymentIntent.client_secret, {
        payment_method: paymentMethodId,
      })
      .then((result) => {
        if (result.error) {
          // start code flow to handle updating the payment details
          // Display error message in your UI.
          // The card was declined (i.e. insufficient funds, card has expired, etc)
          throw result;
        } else {
          if (result.paymentIntent.status === 'succeeded') {
            // There's a risk of the customer closing the window before callback
            // execution. To handle this case, set up a webhook endpoint and
            // listen to invoice.paid. This webhook endpoint returns an Invoice.
            return {
              subscription, priceId, paymentMethodId
            };
          }
        }
      });
  } else {
    // No customer action needed
    return { subscription, priceId, paymentMethodId };
  }
}


function handleRequiresPaymentMethod({
  subscription,
  paymentMethodId,
  priceId,
}) {
  console.log("6 - handleRequiresPaymentMethod()");
  if (subscription.status === 'active') {
    // subscription is active, no customer actions required.
    console.log("return immediately()");
    return {subscription, priceId, paymentMethodId};
  } else if (
    subscription.latest_invoice.payment_intent &&
    subscription.latest_invoice.payment_intent.status ===
    'requires_payment_method'
  ) {
    // Using localStorage to store the state of the retry here
    // (feel free to replace with what you prefer)
    // Store the latest invoice ID and status
    console.log("card was declined");
    throw { error: { message: 'Your card was declined.' } };
  } else {
    console.log("return");
    return {subscription, priceId, paymentMethodId};
  }
}


function onSubscriptionComplete({subscription, priceId, paymentMethodId}) {
  console.log("7 - onSubscriptionComplete()");
  // Payment was successful.
  rewardful('convert', { email: config.customerEmail });
  reloadBilling();
  // if (result.subscription.status === 'active') {
  //   // Change your UI to show a success message to your customer.
  //   // Call your backend to grant access to your service based on
  //   // `result.subscription.items.data[0].price.product` the customer subscribed to.
  // }
}

function reloadBilling() {
  console.log("8 - reloadBilling");
  $(".reloadContainer").click();
}











// function createSubscription(productId) {
//   return fetch('/create-subscription', {
//     method: 'post',
//     headers: {
//       'Content-Type': 'application/json',
//     },
//     body: JSON.stringify({
//       "productId": productId,
//     }),
//   })
//     .then((response) => {
//       $(".reloadContainer").click();
//     })
//     .catch((error) => {
//       // An error has happened. Display the failure to the user here.
//       // We utilize the HTML element we created.
//       displayError(error);
//     })
// }


function cancelSubscription(productId) {
  console.log("1 - cancelSubscription()");
  return fetch('/cancel-subscription', {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      "productId": productId,
    }),
  })
    .then((response) => {
      reloadBilling();
    })
    .catch((error) => {
      // An error has happened. Display the failure to the user here.
      // We utilize the HTML element we created.
      displayError(error);
    })
}



function stopAnimation() {
}
