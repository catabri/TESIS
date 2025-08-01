import os
# Configuración para multiprocessing con numpy
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MKL_DOMAIN_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# Ruta al paquete GF7013
this_module_folder = os.path.dirname(os.path.abspath(__file__))
GF7013_path = os.path.abspath(os.path.join(this_module_folder, '../../../..'))
sys.path.append(GF7013_path)

# Importaciones desde GF7013
from GF7013.bin.Tarea2.P1.datos import obtener_datos_elipses
from GF7013.models.ajuste_ortogonal_recta.forward import forward
from GF7013.model_parameters import ensemble
from GF7013.probability_functions.pdf.pdf_uniform_nD import pdf_uniform_nD
from GF7013.probability_functions.pdf.pdf_normal import pdf_normal
from GF7013.probability_functions.likelihood.likelihood_function import likelihood_function
from GF7013.sampling.metropolis.proposal_normal import proposal_normal
from GF7013.sampling.tmcmc.tmcmc_resampling import tmcmc_pool
class forward_ensemble(forward):   
    def eval(self, m):
        """
        Computes a prediction of the model parameters (see description in this
        module docstring).
        - m = NP.array([a, theta]) with theta in degrees (both float quantities). 
          -> a is the distance between straight line to origin of coordinate system and 
          -> theta is the orientation of the straight line measured counter-clockwise 
            measured from x axis. 
        """
        if isinstance(m, ensemble):
            dpred = np.zeros((m.Nmodels, len(self.x_obs)))
            for i in range(m.Nmodels):
                dpred = super().eval(m.m_set[i, :])
            return dpred
        else:
            return super().eval(m)
        
if __name__ == "__main__":
    N = 50
    semi_eje_mayor = 20
    semi_eje_menor = 2
    alpha = 45
    delta_x = 0
    delta_y = 0
    desviacion_estandar_x = 1.0
    desviacion_estandar_y = 1.0

    x_obs, y_obs, sigma_x, sigma_y = obtener_datos_elipses(
                                            N = N,
                                            a = semi_eje_mayor,
                                            b = semi_eje_menor,
                                            alpha = alpha,
                                            deltax = delta_x,
                                            deltay = delta_y,
                                            sigma_x = desviacion_estandar_x,
                                            sigma_y = desviacion_estandar_y)



    a_min = -15
    a_max = 15
    theta_min = -360
    theta_max = 360 

    lower_lim = np.array([a_min, theta_min])
    upper_lim = np.array([a_max, theta_max])

    par = {
        'lower_lim': lower_lim,
        'upper_lim': upper_lim
    }

    fprior = pdf_uniform_nD(par)

    ############## Creo que de aqui pa bajo ojito
    modelo_forward = forward_ensemble(x_obs=x_obs, y_obs=y_obs, sigma_x=sigma_x, sigma_y=sigma_y)
    # Crear la distribución de probabilidad para los datos (residuos normalizados)
    # Como forward.eval() devuelve residuos normalizados, usamos una normal estándar
    # El número de parámetros debe coincidir con el número de observaciones
    n_obs = len(x_obs)


    # Parámetros teóricos
    par = {'mu': np.zeros(n_obs), 'cov': np.eye(n_obs)}
    pdf = pdf_normal(par)

    # Crear la función de verosimilitud usando tu clase del paquete
    # Función de verosimilitud
    use_log_likelihood = True   ######### LO MAS PRECISO 
    likelihood_fun = likelihood_function(forward=modelo_forward, pdf_data=pdf)
    # Definir la distribución de propuesta (normal multivariada)
    # Matriz de covarianza para la propuesta
    sigma_a = 0.5  # desviación estándar para el parámetro 'a'
    sigma_theta = 0.5  # desviación estándar para el parámetro 'theta'
    cov_matrix = np.array([[sigma_a**2, 0], 
                        [0, sigma_theta**2]])


    proposal = proposal_normal(cov=cov_matrix)


    # Ensemble inicial
    Nmodels = 10000
    beta0 = 0.0
    m0 = ensemble(Npar=2, Nmodels=Nmodels, use_log_likelihood=use_log_likelihood, beta=beta0)
    m0.m_set = fprior.draw(Nmodels).T

    # TMCMC
    m_final, acc_ratios = tmcmc_pool(m0, likelihood_fun,
                                pdf_prior=fprior,
                                proposal=proposal,
                                num_MCMC_steps=300,
                                num_proc=6,
                                chunksize=1,
                                use_resampling=True)

    print(f"\nTMCMC terminado. Beta final: {m_final.beta}")
    print("Razones de aceptación:")
    print(acc_ratios)

    # Extraer muestras
    #cadenas?
    a_samples = m_final.m_set[:, 0]
    theta_samples = m_final.m_set[:, 1]
    print(f'shape a_samples: {a_samples.shape}')    
    print(f'shape theta_samples: {theta_samples.shape}')


    # --- Graficar evolución de parámetros ---
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)

    sc=ax.scatter(a_samples,theta_samples,alpha=0.7,c=np.arange(len(a_samples)),cmap='rainbow')
    plt.colorbar(sc, ax=ax, label='Índice de Muestra')
    ax.set_xlabel('a')
    ax.set_ylabel('theta [grados]')
    ax.grid(True)

    plt.suptitle("Evolución de la cadena de Metropolis (30% Burn-in)", fontsize=16)
    plt.tight_layout()
    plt.show()

    # # --- Graficar histogramas de parámetros ---
    # fig = plt.figure(figsize=(10, 8))
    # gs = gridspec.GridSpec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
    #                        wspace=0.05, hspace=0.05)
    # ax_join = fig.add_subplot(gs[1, 0])
    # counts, xedges, yedges, im = ax_join.hist2d(a_samples, theta_samples, bins=50, cmap='viridis')
    # fig.colorbar(im, ax=ax_join, label='Cuentas')
    # ax_join.set_title('Histograma 2D (PDF conjunta)')
    # ax_join.set_xlabel('a')
    # ax_join.set_ylabel('theta [grados]')

    # # Marginal para a
    # ax_a = fig.add_subplot(gs[0, 0], sharex=ax_join)
    # a_hist, a_bins, _ = ax_a.hist(a_samples, bins=100, density=True, alpha=0.6, color='blue', label='Histograma de a')
    # ax_a.set_title('Marginal para a')
    # ax_a.set_ylabel('Densidad')
    # ax_a.legend()
    # ax_a.tick_params(labelbottom=False)
    # pos = ax_a.get_position()
    # ax_a.set_position([pos.x0, pos.y0 + 0.03, pos.width, pos.height])

    # # Marginal para theta
    # ax_theta = fig.add_subplot(gs[1, 1], sharey=ax_join)
    # theta_hist, theta_bins, _ = ax_theta.hist(theta_samples, bins=100, density=True, alpha=0.6, color='green', orientation='horizontal', label='Histograma de theta')
    # ax_theta.set_title('Marginal para theta')
    # ax_theta.set_xlabel('Densidad')
    # ax_theta.legend()
    # ax_theta.tick_params(labelleft=False)   
    # fig.suptitle("Distribución de Parámetros: Histograma Conjunto y Marginales", fontsize=14, y=0.965)
    # plt.tight_layout(rect=[0, 0, 1, 0.95])
    # plt.show()


    # Histograma conjunto y marginales
    fig = plt.figure(figsize=(10, 8))
    gs = gridspec.GridSpec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
                        wspace=0.05, hspace=0.05)
    ax_join = fig.add_subplot(gs[1, 0])
    counts, xedges, yedges, im = ax_join.hist2d(a_samples, theta_samples, bins=50, cmap='viridis')
    fig.colorbar(im, ax=ax_join, label='Cuentas')
    ax_join.set_title('Histograma 2D posterior')
    ax_join.set_xlabel('a')
    ax_join.set_ylabel('theta [°]')

    # Marginal para a
    ax_a = fig.add_subplot(gs[0, 0], sharex=ax_join)
    ax_a.hist(a_samples, bins=100, density=True, alpha=0.6, color='blue')
    ax_a.set_title('Marginal de a')
    ax_a.tick_params(labelbottom=False)

    # Marginal para theta
    ax_theta = fig.add_subplot(gs[1, 1], sharey=ax_join)
    ax_theta.hist(theta_samples, bins=100, density=True, alpha=0.6, color='green', orientation='horizontal')
    ax_theta.set_title('Marginal de θ')
    ax_theta.tick_params(labelleft=False)

    fig.suptitle("Posterior: TMCMC para ajuste ortogonal", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()