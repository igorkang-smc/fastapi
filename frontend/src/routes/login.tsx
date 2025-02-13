import {ViewIcon, ViewOffIcon} from "@chakra-ui/icons"
import {
    Button,
    Container,
    FormControl,
    FormErrorMessage,
    Icon,
    Image,
    Input,
    InputGroup,
    InputRightElement,
    Link,
    Text,
    useBoolean,
} from "@chakra-ui/react"
import {
    Link as RouterLink,
    createFileRoute,
    redirect,
} from "@tanstack/react-router"
import {type SubmitHandler, useForm} from "react-hook-form"
import googleOneTap from 'google-one-tap'
import Logo from "/assets/images/fastapi-logo.svg"
import type {Body_login_login_access_token as AccessToken} from "../client"
import useAuth, {isLoggedIn} from "../hooks/useAuth"
import {emailPattern} from "../utils"
import {useEffect} from "react";


export const Route = createFileRoute("/login")({
    component: Login,
    beforeLoad: async () => {
        if (isLoggedIn()) {
            throw redirect({
                to: "/",
            })
        }
    },
})

function Login() {
    const [show, setShow] = useBoolean()
    const {loginMutation, error, resetError} = useAuth()
    const {
        register,
        handleSubmit,
        formState: {errors, isSubmitting},
    } = useForm<AccessToken>({
        mode: "onBlur",
        criteriaMode: "all",
        defaultValues: {
            username: "",
            password: "",
        },
    })


    useEffect(() => {
        const options = {
            client_id: '576963665063-b0as1vrt1f4cmgrk5j7t2pjh2iqaj2mg.apps.googleusercontent.com',
            auto_select: false,
            cancel_on_tap_outside: false,
            context: 'signin'
        }

        // @ts-ignore
        googleOneTap(options, (response: any) => {
            console.log(response)
            if (response && response.credential) {
                // Decode the JWT credential
                //send response.credential to fastapi
                fetch('http://localhost:8000/api/v1/google_login/access_token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({"google_token": response.credential}),
                })
                    .then(response => response.json())
                    .then(data => {
                        // Handle response, typically storing the JWT token
                        console.log(data)
                        localStorage.setItem('access_token', data.access_token);
                    })
                    .catch(err => console.error(err));
            } else {
                console.error('No credential received or invalid response.');
            }
        })
    })

    const onSubmit: SubmitHandler<AccessToken> = async (data) => {
        if (isSubmitting) return

        resetError()

        try {
            await loginMutation.mutateAsync(data)
        } catch {
            // error is handled by useAuth hook
        }
    }

    return (
        <>
            <Container
                as="form"
                onSubmit={handleSubmit(onSubmit)}
                h="100vh"
                maxW="sm"
                alignItems="stretch"
                justifyContent="center"
                gap={4}
                centerContent
            >
                <Image
                    src={Logo}
                    alt="FastAPI logo"
                    height="auto"
                    maxW="2xs"
                    alignSelf="center"
                    mb={4}
                />
                <FormControl id="username" isInvalid={!!errors.username || !!error}>
                    <Input
                        id="username"
                        {...register("username", {
                            required: "Username is required",
                            pattern: emailPattern,
                        })}
                        placeholder="Email"
                        type="email"
                        required
                    />
                    {errors.username && (
                        <FormErrorMessage>{errors.username.message}</FormErrorMessage>
                    )}
                </FormControl>
                <FormControl id="password" isInvalid={!!error}>
                    <InputGroup>
                        <Input
                            {...register("password", {
                                required: "Password is required",
                            })}
                            type={show ? "text" : "password"}
                            placeholder="Password"
                            required
                        />
                        <InputRightElement
                            color="ui.dim"
                            _hover={{
                                cursor: "pointer",
                            }}
                        >
                            <Icon
                                as={show ? ViewOffIcon : ViewIcon}
                                onClick={setShow.toggle}
                                aria-label={show ? "Hide password" : "Show password"}
                            >
                                {show ? <ViewOffIcon/> : <ViewIcon/>}
                            </Icon>
                        </InputRightElement>
                    </InputGroup>
                    {error && <FormErrorMessage>{error}</FormErrorMessage>}
                </FormControl>
                <Link as={RouterLink} to="/recover-password" color="blue.500">
                    Forgot password?
                </Link>
                <Button variant="primary" type="submit" isLoading={isSubmitting}>
                    Log In
                </Button>
                <Text>
                    Don't have an account?{" "}
                    <Link as={RouterLink} to="/signup" color="blue.500">
                        Sign up
                    </Link>
                </Text>
            </Container>
        </>
    )
}
