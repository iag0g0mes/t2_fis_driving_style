import numpy as np
#np.set_printoptions(precision=2)

import pandas as pd

from typing import Any, Dict, List, Tuple, NoReturn

import argparse
import os
import pickle
import json

from sklearn.mixture import GaussianMixture

def parse_arguments() -> Any:
	"""Parse command line arguments."""

	parser = argparse.ArgumentParser()
	
	parser.add_argument(
		"--data_dir",
		required=True,
		type=str,
		help="Directory where the features (npy files) are saved",
	)

	parser.add_argument(
		"--model_dir",
		required=True,
		type=str,
		help="Directory where the model is saved",
	)

	parser.add_argument(
		"--result_dir",
		required=True,
		type=str,
		help="Directory where the model is saved",
	)


	parser.add_argument("--mode",
						required=True,
						type=str,
						help="train/val/test",
						choices=['train', 'test', 'val'])

	parser.add_argument("--obs_len",
						default=2,
						type=int,
						help="Observed length of the trajectory in seconds",
						choices=[1,2,3,4,5])

	parser.add_argument("--filter",
						default='ekf',
						type=str,
						help="Filter to process the data noise. (ekf/none/ekf-savgol/savgol",
						choices=['ekf', 'none', 'ekf-savgol', 'savgol'])

	return parser.parse_args()


def train(data:np.ndarray,
		  obs_len:int,
		  filter_name:str,
		  model_dir:str,
		  result_dir:str,
		  save_model:bool=True)->NoReturn:
	
	print('[Gaussian Mixture Clustering][train] creating model...')

	gmc = GaussianMixture(n_components=3,
						  covariance_type="full",
						  max_iter=1000,
						  tol=1e-5,
						  n_init=10,
						  random_state=7,
						  init_params="kmeans")

	print('[Gaussian Mixture Clustering][train] training...')

	_y = gmc.fit_predict(X=data)
	_y = np.expand_dims(_y, axis=1)

	print(f'[Gaussian Mixture Clustering][train] converged?:{gmc.converged_}')

	print('[Gaussian Mixture Clustering][train] params (center and covariance):')
	for i, m, c in zip(range(1, 4), gmc.means_, gmc.covariances_):
		print(f'\tc_{i}-> mean: {m}')
		print(f'\t\tcov: {c}')

	print('[Gaussian Mixture Clustering][train] results:')
	_c, _l = np.unique(_y, return_counts=True)
	for i, c in zip(_c,_l):
		print (f'\tc_{i}: {c}')

	if save_model:
		model_file=f'gmc_{obs_len}s_{filter_name}.pkl'
		print (f'[Gaussian Mixture Clustering][train] saving model ({model_file})...')
		with open(os.path.join(model_dir, model_file), 'wb') as f:
			pickle.dump(gmc, f)


	result_file = f'results_gmc_train_{obs_len}s_{filter_name}.csv'
	print (f'[Gaussian Mixture Clustering][train] saving results ({result_file})...')
	labels = ['mean_velocity', 
			  'mean_acceleration', 
			  'mean_deceleration', 
			  'std_lateral_jerk', 
			  'driving_style']

	result = np.concatenate((data, _y), axis=1)
	df = pd.DataFrame(data=result, columns=labels)
	df.to_csv(os.path.join(result_dir,result_file))

	result_file = result_file.replace('results', 'params').replace('csv', 'json')
	print (f'[Gaussian Mixture Clustering][train] saving results ({result_file})...')
	_d = {}
	_d['means'] = gmc.means_.tolist()
	_d['covariances'] = gmc.covariances_.tolist()
	with open(os.path.join(result_dir, result_file), 'w') as f:
		json.dump(_d, f)


def process(data:np.ndarray,
		    obs_len:int,
		    filter_name:str,
		    model_dir:str,
		    result_dir:str,
		    mode:str)->NoReturn:

	model_file=f'gmc_{obs_len}s_{filter_name}.pkl'
	assert os.path.exists(os.path.join(model_dir, model_file)),\
		f'[Gaussian Mixture Clustering][{mode}][ERROR] model not found! ({model_file})'

	print(f'[Gaussian Mixture Clustering][{mode}] loading the model...')
	gmc = None
	with open(os.path.join(model_dir, model_file), 'rb') as f:
			gmc = pickle.load(f)
	
	assert gmc is not None,\
		f'[Gaussian Mixture Clustering][{mode}][ERROR] error while loading model! ({model_file})'

	_y = gmc.predict(X=data)
	_y = np.expand_dims(_y, axis=1)

	print(f'[Gaussian Mixture Clustering][{mode}] converged?:{gmc.converged_}')

	print(f'[Gaussian Mixture Clustering][{mode}] params (center and covariance):')
	for i, m, c in zip(range(1, 4), gmc.means_, gmc.covariances_):
		print(f'\tc_{i}-> mean: {m}')
		print(f'\t\tcov: {c}')

	print(f'[Gaussian Mixture Clustering][{mode}] results:')
	_c, _l = np.unique(_y, return_counts=True)
	for i, c in zip(_c,_l):
		print (f'\tc_{i}: {c}')


	result_file = f'results_gmc_{mode}_{obs_len}s_{filter_name}.csv'
	print (f'[Gaussian Mixture Clustering][{mode}] saving results ({result_file})...')
	labels = ['mean_velocity', 
			  'mean_acceleration', 
			  'mean_deceleration', 
			  'std_lateral_jerk', 
			  'driving_style']

	result = np.concatenate((data, _y), axis=1)
	df = pd.DataFrame(data=result, columns=labels)
	df.to_csv(os.path.join(result_dir,result_file))


if __name__ == '__main__':

	'''
		apply Gaussian Mixture Clustering clustering to classify the data into
		driving styles (calm, moderate, aggresive)
	'''

	print ('[Gaussian Mixture Clustering] running....') 

	args = parse_arguments()


	if args.mode == 'test':
		args.obs_len = 2
		
	assert os.path.exists(args.data_dir),\
		f'[Gaussian Mixture Clustering][main][ERROR] data_dir not found!({args.data_dir})'

	data_file = 'features_{}_{}s_{}.npy'.format(args.mode,
				 								args.obs_len,
				 								args.filter)
	data_file = os.path.join(args.data_dir, data_file)

	assert os.path.exists(data_file),\
		f'[Gaussian Mixture Clustering][main][ERROR] data_file not found!({data_file})'

	print ('[Gaussian Mixture Clustering][main] loading dataset....')
	# (m, 4)
	# [mean_v, mean_acc, mean_deac, std_jy]
	data = np.load(os.path.join(args.data_dir,data_file))

	if args.mode == 'train':
		train(data=data,
			  save_model=True,
			  obs_len=args.obs_len,
			  filter_name=args.filter,
			  model_dir=args.model_dir,
			  result_dir=args.result_dir)

	elif args.mode == 'test':
		process(data=data,
			 obs_len=args.obs_len,
			 filter_name=args.filter,
			 model_dir=args.model_dir,
			 result_dir=args.result_dir,
			 mode='test')

	else:#val
		process(data=data,
			 obs_len=args.obs_len,
			 filter_name=args.filter,
			 model_dir=args.model_dir,
			 result_dir=args.result_dir,
			 mode='val')
